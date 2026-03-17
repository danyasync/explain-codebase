from __future__ import annotations

from collections import OrderedDict
from pathlib import Path

from rich.console import Console

from explain_codebase.models.analysis_result import AnalysisResult, FileExplanation


class CliRenderer:
    HEADER = "Explain Codebase\n" + ("─" * 32)
    DEFAULT_LIST_LIMIT = 10

    def render(self, result: AnalysisResult, verbose: bool = False, deep: bool = False) -> None:
        console = Console()
        console.print(self.HEADER)
        console.print()

        self.render_repository_section(console, result)
        architecture_title = "Architecture" if not verbose and not deep else "Architecture summary"
        self.render_architecture_summary(console, result, title=architecture_title)
        self.render_suggested_starting_point(console, result)

        if verbose:
            self.render_entrypoints(console, result)
            self.render_core_modules(console, result)
            self.render_side_effect_modules(console, result)
            self.render_execution_flow(console, result)
            self.render_file_roles(console, result)
            console.print()
            console.print("Run with --deep to see architecture issues")
            return

        if deep:
            self.render_deep_analysis(console, result)
            return

        console.print()
        console.print("Run with --verbose to see full architecture")

    def render_repository_section(self, console: Console, result: AnalysisResult) -> None:
        console.print("Repository")
        console.print()
        console.print(f"  Path        {result.project_root}")
        console.print(f"  Type        {result.project_type}")
        console.print(f"  Language    {', '.join(result.languages) or 'unknown'}")
        console.print(f"  Files       {result.total_files}")
        console.print()

    def render_architecture_summary(self, console: Console, result: AnalysisResult, title: str) -> None:
        console.print(title)
        console.print()
        console.print(f"  Entrypoints        {len(result.entrypoints)}")
        console.print(f"  Core modules       {len(result.core_modules)}")
        console.print(f"  Side effects       {len(result.side_effect_modules)}")
        console.print()

    def render_suggested_starting_point(self, console: Console, result: AnalysisResult) -> None:
        console.print("Suggested starting point")
        console.print()
        console.print(f"  {self._suggested_starting_point(result)}")

    def render_entrypoints(self, console: Console, result: AnalysisResult) -> None:
        console.print()
        console.print("Entrypoints")
        console.print()
        for item in self._limit_list(result.entrypoints):
            console.print(f"  {item}")
        if not result.entrypoints:
            console.print("  None detected")

    def render_core_modules(self, console: Console, result: AnalysisResult) -> None:
        console.print()
        title = self._title_with_limit("Core modules", len(result.core_module_rankings))
        console.print(title)
        console.print()
        if result.core_module_rankings:
            for item in result.core_module_rankings[: self.DEFAULT_LIST_LIMIT]:
                console.print(f"  {item.path}")
        else:
            console.print("  None detected")

    def render_side_effect_modules(self, console: Console, result: AnalysisResult) -> None:
        console.print()
        title = self._title_with_limit("Side-effect modules", len(result.side_effect_modules))
        console.print(title)
        console.print()
        for item in self._limit_list(result.side_effect_modules):
            console.print(f"  {item}")
        if not result.side_effect_modules:
            console.print("  None detected")

    def render_execution_flow(self, console: Console, result: AnalysisResult) -> None:
        console.print()
        console.print("Execution flow")
        console.print()
        lines = self._render_execution_flow_lines(result.execution_flow)
        if not lines:
            console.print("  No clear execution flow inferred")
            return
        for line in lines:
            console.print(line)

    def render_file_roles(self, console: Console, result: AnalysisResult) -> None:
        console.print()
        title = self._title_with_limit("File roles", len(result.file_roles))
        console.print(title)
        console.print()
        items = list(sorted(result.file_roles.items()))[: self.DEFAULT_LIST_LIMIT]
        if not items:
            console.print("  None detected")
            return

        width = max(len(path) for path, _ in items)
        for path, role in items:
            console.print(f"  {path.ljust(width)}  {role}")

    def render_deep_analysis(self, console: Console, result: AnalysisResult) -> None:
        console.print()
        console.print("Architecture issues")
        console.print()
        if result.architecture_issues:
            for issue in result.architecture_issues[: self.DEFAULT_LIST_LIMIT]:
                console.print(self._format_issue_title(issue.issue_type))
                console.print(f"  {self._format_issue_body(issue.issue_type, issue.description)}")
                console.print()
        else:
            console.print("  No architecture issues detected")
            console.print()

        console.print(self._title_with_limit("Large modules", len(result.large_files)))
        console.print()
        if result.large_files:
            for item in result.large_files[: self.DEFAULT_LIST_LIMIT]:
                console.print(f"  {item.path} ({item.loc} LOC)")
        else:
            console.print("  None detected")

        console.print()
        console.print(self._title_with_limit("High coupling modules", len(result.hotspots)))
        console.print()
        if result.hotspots:
            for item in result.hotspots[: self.DEFAULT_LIST_LIMIT]:
                console.print(f"  {item.path}")
        else:
            console.print("  None detected")

    def render_onboarding(self, project_root: str, onboarding_path: list[str]) -> None:
        console = Console()
        console.print(self.HEADER)
        console.print()
        console.print("Repository")
        console.print()
        console.print(f"  Path        {project_root}")
        console.print()
        console.print("Suggested starting points")
        console.print()
        if onboarding_path:
            for index, path in enumerate(onboarding_path, start=1):
                console.print(f"  {index}. {path}")
        else:
            console.print("  No recommended reading path inferred")

    def render_file_explanation(self, explanation: FileExplanation) -> None:
        console = Console()
        console.print(self.HEADER)
        console.print()
        console.print("File")
        console.print()
        console.print(f"  Path        {explanation.path}")
        console.print(f"  Role        {explanation.role}")
        console.print(f"  Lines       {explanation.line_count}")
        console.print(f"  Used by     {explanation.incoming_imports}")
        console.print(f"  Depends on  {explanation.outgoing_imports}")
        console.print()
        self._render_simple_list(console, "Used by", explanation.used_by)
        self._render_simple_list(console, "Depends on", explanation.depends_on)
        self._render_simple_list(console, "Responsibilities", explanation.responsibilities)

    def _render_simple_list(self, console: Console, title: str, values: list[str]) -> None:
        console.print(title)
        console.print()
        if values:
            for value in values[: self.DEFAULT_LIST_LIMIT]:
                console.print(f"  {value}")
        else:
            console.print("  None detected")
        console.print()

    def _suggested_starting_point(self, result: AnalysisResult) -> str:
        if result.entrypoints:
            return result.entrypoints[0]
        if result.core_module_rankings:
            return result.core_module_rankings[0].path
        if result.core_modules:
            return result.core_modules[0]
        if result.file_roles:
            return sorted(result.file_roles)[0]
        return "No clear starting point inferred"

    def _limit_list(self, values: list[str]) -> list[str]:
        return values[: self.DEFAULT_LIST_LIMIT]

    def _title_with_limit(self, title: str, count: int) -> str:
        if count > self.DEFAULT_LIST_LIMIT:
            return f"{title} (top {self.DEFAULT_LIST_LIMIT})"
        return title

    def _render_execution_flow_lines(self, flows: list[list[str]]) -> list[str]:
        tree: OrderedDict[str, OrderedDict] = OrderedDict()
        for flow in flows:
            current = tree
            for node in flow:
                current = current.setdefault(node, OrderedDict())

        lines: list[str] = []
        root_items = list(tree.items())[: self.DEFAULT_LIST_LIMIT]
        for index, (root, children) in enumerate(root_items):
            lines.append(root)
            lines.extend(self._render_tree_children(children, prefix=""))
            if index < len(root_items) - 1:
                lines.append("")
        return lines

    def _render_tree_children(self, children: OrderedDict[str, OrderedDict], prefix: str) -> list[str]:
        lines: list[str] = []
        items = list(children.items())[: self.DEFAULT_LIST_LIMIT]
        for index, (name, subtree) in enumerate(items):
            is_last = index == len(items) - 1
            branch = "└─ " if is_last else "├─ "
            lines.append(f"{prefix}{branch}{name}")
            child_prefix = f"{prefix}{'   ' if is_last else '│  '}"
            lines.extend(self._render_tree_children(subtree, child_prefix))
        return lines

    def _format_issue_title(self, issue_type: str) -> str:
        label_map = {
            "circular_dependency": "Circular dependency",
            "god_module": "Utility god module",
        }
        return label_map.get(issue_type, issue_type.replace("_", " ").title())

    def _format_issue_body(self, issue_type: str, description: str) -> str:
        prefix_map = {
            "circular_dependency": "Circular dependency: ",
            "god_module": "Utility module too large: ",
        }
        prefix = prefix_map.get(issue_type)
        if prefix and description.startswith(prefix):
            return description[len(prefix) :]
        return description
