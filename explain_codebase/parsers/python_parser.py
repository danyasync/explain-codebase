from __future__ import annotations

import ast
from pathlib import Path

from explain_codebase.models.file_info import FileInfo
from explain_codebase.utils.file_utils import safe_read_text

SIDE_EFFECT_IMPORT_CATEGORIES = {
    "aiohttp": "network",
    "asyncpg": "database",
    "aioredis": "cache",
    "httpx": "network",
    "motor": "database",
    "mysql": "database",
    "psycopg": "database",
    "psycopg2": "database",
    "pymongo": "database",
    "redis": "cache",
    "requests": "network",
    "sqlalchemy": "database",
    "sqlite3": "database",
    "urllib": "network",
}

SIDE_EFFECT_CALL_PREFIXES = {
    "aiohttp.": "network",
    "engine.connect": "database",
    "httpx.": "network",
    "open": "filesystem",
    "pathlib.path.read_text": "filesystem",
    "pathlib.path.write_text": "filesystem",
    "read_text": "filesystem",
    "redis.": "cache",
    "requests.": "network",
    "session.execute": "database",
    "shutil.": "filesystem",
    "sqlite3.connect": "database",
    "urlopen": "network",
    "urllib.": "network",
    "write_text": "filesystem",
}

FILESYSTEM_CALL_SUFFIXES = {
    ".open",
    ".read_bytes",
    ".read_text",
    ".write_bytes",
    ".write_text",
}

FILESYSTEM_CALL_NAMES = {
    "os.mkdir",
    "os.makedirs",
    "os.remove",
    "os.rename",
    "os.replace",
    "os.rmdir",
    "os.scandir",
    "os.unlink",
    "os.walk",
}

ROUTE_DECORATOR_NAMES = {
    "api_route",
    "delete",
    "get",
    "head",
    "options",
    "patch",
    "post",
    "put",
    "route",
    "trace",
    "websocket",
    "websocket_route",
}

APP_RUN_CALLS = {
    "app.run",
    "uvicorn.run",
}

CLI_CALLS = {
    "click.command",
    "typer.run",
}


class PythonParser:
    def parse(self, path: Path, root_path: Path) -> FileInfo:
        content = safe_read_text(path, root_path=root_path)
        relative_path = path.relative_to(root_path).as_posix()
        info = FileInfo(
            path=relative_path,
            language="python",
            line_count=len(content.splitlines()),
        )

        try:
            tree = ast.parse(content)
        except SyntaxError:
            info.parse_error = True
            return info

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    info.imports.append(alias.name)
                    info.import_groups.append([alias.name])
                    self._register_side_effect_import(info, alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                import_base = "." * node.level + module
                import_group: list[str] = []
                if import_base:
                    info.imports.append(import_base)
                    import_group.append(import_base)
                if not node.level and module:
                    self._register_side_effect_import(info, module)
                for alias in node.names:
                    if alias.name == "*":
                        continue
                    separator = "" if import_base.endswith(".") else "."
                    imported_member = f"{import_base}{separator}{alias.name}" if import_base else alias.name
                    if imported_member != import_base:
                        info.imports.append(imported_member)
                        import_group.append(imported_member)
                if import_group:
                    info.import_groups.append(import_group)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._register_function(info, node)
            elif isinstance(node, ast.ClassDef):
                info.classes.append(node.name)
            elif isinstance(node, ast.Call):
                call_name = self._expr_name(node.func)
                if call_name:
                    info.function_calls.append(call_name)
                    lowered = call_name.lower()
                    if lowered in APP_RUN_CALLS:
                        info.has_app_run = True
                    if lowered in CLI_CALLS or lowered == "argparse" or lowered.startswith("argparse."):
                        info.has_cli_signal = True
                    self._register_side_effect_call(info, lowered)
            elif isinstance(node, ast.If) and self._is_main_guard(node):
                info.has_main_guard = True

        return info

    def _expr_name(self, node: ast.AST) -> str | None:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            prefix = self._expr_name(node.value)
            return f"{prefix}.{node.attr}" if prefix else node.attr
        if isinstance(node, ast.Call):
            return self._expr_name(node.func)
        return None

    def _register_function(self, info: FileInfo, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        info.functions.append(node.name)
        for decorator in node.decorator_list:
            decorator_name = self._expr_name(decorator)
            if not decorator_name:
                continue
            info.decorators.append(decorator_name)
            if decorator_name.rsplit(".", 1)[-1].lower() in ROUTE_DECORATOR_NAMES:
                info.route_handlers.append(node.name)

    def _is_main_guard(self, node: ast.If) -> bool:
        test = node.test
        if not isinstance(test, ast.Compare):
            return False
        if len(test.ops) != 1 or not isinstance(test.ops[0], ast.Eq) or len(test.comparators) != 1:
            return False
        left, right = test.left, test.comparators[0]
        return (
            self._is_name_variable(left)
            and self._is_main_constant(right)
            or self._is_main_constant(left)
            and self._is_name_variable(right)
        )

    def _is_name_variable(self, node: ast.AST) -> bool:
        return isinstance(node, ast.Name) and node.id == "__name__"

    def _is_main_constant(self, node: ast.AST) -> bool:
        return isinstance(node, ast.Constant) and node.value == "__main__"

    def _register_side_effect_import(self, info: FileInfo, module_name: str) -> None:
        root_module = module_name.split(".")[0].lower()
        category = SIDE_EFFECT_IMPORT_CATEGORIES.get(root_module)
        if category is not None:
            self._add_side_effect(info, category)

    def _register_side_effect_call(self, info: FileInfo, call_name: str) -> None:
        if call_name in FILESYSTEM_CALL_NAMES or any(call_name.endswith(suffix) for suffix in FILESYSTEM_CALL_SUFFIXES):
            self._add_side_effect(info, "filesystem")
        for prefix, category in SIDE_EFFECT_CALL_PREFIXES.items():
            if call_name == prefix or (prefix.endswith(".") and call_name.startswith(prefix)):
                self._add_side_effect(info, category)

    def _add_side_effect(self, info: FileInfo, category: str) -> None:
        if category not in info.side_effects:
            info.side_effects.append(category)
        info.has_side_effects = True
