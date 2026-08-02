from __future__ import annotations

import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

import click
import typer

from explain_codebase.utils.git_utils import hardened_git_runtime
from explain_codebase.utils.output_utils import terminal_safe_text


@dataclass
class ResolvedTarget:
    analysis_path: Path
    cleanup_path: Path | None = None
    source: str = "local"
    original_target: str = ""


@dataclass
class GitHubRepository:
    owner: str
    repo: str
    clone_url: str
    display_url: str
    api_url: str


class TargetResolver:
    TOTAL_STEPS = 5
    CLONE_TIMEOUT_SECONDS = 120

    def resolve(self, target: str) -> ResolvedTarget:
        normalized_target = target.strip() or "."
        self._print_stage(1, "Resolving target...")

        github_repository = self._parse_github_repository(normalized_target)
        if github_repository is not None:
            return self._resolve_remote_target(github_repository)

        self._print_stage(2, "Preparing local repository...")
        local_path = Path(normalized_target).expanduser().resolve()
        if not local_path.exists() or not local_path.is_dir():
            raise typer.BadParameter(f"Target directory does not exist: {normalized_target}")

        return ResolvedTarget(
            analysis_path=local_path,
            source="local",
            original_target=normalized_target,
        )

    def cleanup(self, resolved: ResolvedTarget) -> None:
        if resolved.cleanup_path is None:
            return

        typer.echo("Cleaning temporary workspace...", err=True)
        shutil.rmtree(resolved.cleanup_path, ignore_errors=True)
        typer.echo("Temporary workspace removed", err=True)

    def _resolve_remote_target(self, repository: GitHubRepository) -> ResolvedTarget:
        repository_status = self._check_repository_access(repository)
        if repository_status == "not_found":
            self._print_remote_not_found(repository.display_url)
            raise typer.Exit(code=1)
        if repository_status == "not_accessible":
            self._print_remote_not_accessible(repository.display_url)
            raise typer.Exit(code=1)

        self._print_repository_reference(repository.display_url)

        answer = self._ask_yes_no("Download repository into a temporary directory? (y/n): ")
        if not answer:
            typer.echo("Operation cancelled", err=True)
            raise typer.Exit(code=0)

        temp_dir = Path(tempfile.mkdtemp(prefix="explain_codebase_")).resolve()
        typer.echo("Temporary workspace", err=True)
        typer.echo(f"  {terminal_safe_text(temp_dir)}", err=True)
        typer.echo("", err=True)

        try:
            self._print_stage(2, "Cloning repository...")
            self._clone_repository(repository.clone_url, temp_dir)
        except FileNotFoundError:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise click.ClickException("Git is required to analyze a remote repository.") from None
        except subprocess.TimeoutExpired:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise click.ClickException(
                f"Repository clone exceeded the {self.CLONE_TIMEOUT_SECONDS}-second time limit."
            ) from None
        except subprocess.CalledProcessError:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise click.ClickException("Git could not clone the requested public repository.") from None
        except OSError as error:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise click.ClickException(f"Could not prepare the remote repository: {error}") from None

        return ResolvedTarget(
            analysis_path=temp_dir,
            cleanup_path=temp_dir,
            source="remote",
            original_target=repository.display_url,
        )

    def _clone_repository(self, target: str, destination: Path) -> None:
        with hardened_git_runtime() as (command_prefix, environment):
            subprocess.run(
                [
                    *command_prefix,
                    "-c",
                    "credential.helper=",
                    "clone",
                    "--depth=1",
                    "--single-branch",
                    "--no-tags",
                    "--",
                    target,
                    str(destination),
                ],
                check=True,
                env=environment,
                timeout=self.CLONE_TIMEOUT_SECONDS,
            )

    def _ask_yes_no(self, prompt: str) -> bool:
        while True:
            typer.echo(prompt, nl=False, err=True)
            try:
                answer = input().strip().lower()
            except EOFError:
                typer.echo("Interactive confirmation is required for remote repositories.", err=True)
                raise typer.Exit(code=2) from None
            if answer in {"y", "yes"}:
                return True
            if answer in {"n", "no"}:
                return False

    def _parse_github_repository(self, target: str) -> GitHubRepository | None:
        parsed = urlparse(target)
        if parsed.scheme != "https" or parsed.netloc.lower() != "github.com":
            return None
        if parsed.params or parsed.query or parsed.fragment:
            return None

        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) != 2:
            return None

        owner, repo_part = parts
        if not owner or not repo_part:
            return None

        repo = repo_part[:-4] if repo_part.endswith(".git") else repo_part
        if not repo:
            return None

        display_url = f"https://github.com/{owner}/{repo}"
        return GitHubRepository(
            owner=owner,
            repo=repo,
            clone_url=f"{display_url}.git",
            display_url=display_url,
            api_url=f"https://api.github.com/repos/{owner}/{repo}",
        )

    def _check_repository_access(self, repository: GitHubRepository) -> str:
        request = Request(
            repository.api_url,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "explain-codebase",
            },
        )
        try:
            # repository.api_url is synthesized from a strict https://github.com/{owner}/{repo} target.
            with urlopen(request, timeout=10) as response:  # nosec B310
                if response.status == 200:
                    return "exists"
        except HTTPError as error:
            if error.code == 404:
                return "not_found"
            if error.code in {401, 403}:
                return "not_accessible"
            return "not_accessible"
        except URLError:
            return "not_accessible"

        return "not_accessible"

    def _print_remote_not_found(self, target: str) -> None:
        typer.echo("Error: Repository not found", err=True)
        typer.echo(terminal_safe_text(target), err=True)
        typer.echo("Make sure the repository exists and is publicly accessible.", err=True)

    def _print_remote_not_accessible(self, target: str) -> None:
        typer.echo("Error: Repository is not accessible", err=True)
        typer.echo(terminal_safe_text(target), err=True)
        typer.echo("Only public repositories are supported.", err=True)

    def _print_stage(self, step: int, message: str) -> None:
        typer.echo(f"[{step}/{self.TOTAL_STEPS}] {message}", err=True)

    def _print_repository_reference(self, target: str) -> None:
        typer.echo("Repository", err=True)
        typer.echo(f"  {terminal_safe_text(target)}", err=True)
        typer.echo("", err=True)
