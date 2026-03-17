from __future__ import annotations

from explain_codebase.models.file_info import FileInfo


class EntrypointFinder:
    def find(self, files: list[FileInfo]) -> list[str]:
        result = []
        for file in files:
            if any(
                [
                    file.has_main_guard,
                    file.has_app_run,
                    file.has_app_listen,
                    file.has_create_server,
                    file.has_cli_signal,
                    file.role == "entrypoint",
                ]
            ):
                result.append(file.path)
        return sorted(set(result))
