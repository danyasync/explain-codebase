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
    "os": "filesystem",
    "pathlib": "filesystem",
    "psycopg": "database",
    "psycopg2": "database",
    "pymongo": "database",
    "redis": "cache",
    "requests": "network",
    "shutil": "filesystem",
    "sqlalchemy": "database",
    "sqlite3": "database",
    "tempfile": "filesystem",
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


class PythonParser:
    def parse(self, path: Path, root_path: Path) -> FileInfo:
        content = safe_read_text(path)
        relative_path = path.relative_to(root_path).as_posix()
        info = FileInfo(
            path=relative_path,
            language="python",
            line_count=len(content.splitlines()),
        )

        try:
            tree = ast.parse(content)
        except SyntaxError:
            return info

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    info.imports.append(alias.name)
                    self._register_side_effect_import(info, alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if node.level:
                    info.imports.append("." * node.level + module)
                elif module:
                    info.imports.append(module)
                    self._register_side_effect_import(info, module)
            elif isinstance(node, ast.FunctionDef):
                info.functions.append(node.name)
                for decorator in node.decorator_list:
                    decorator_name = self._expr_name(decorator)
                    if decorator_name:
                        info.decorators.append(decorator_name)
                        if any(signal in decorator_name.lower() for signal in ["get", "post", "put", "delete", "route"]):
                            info.route_handlers.append(node.name)
            elif isinstance(node, ast.AsyncFunctionDef):
                info.functions.append(node.name)
            elif isinstance(node, ast.ClassDef):
                info.classes.append(node.name)
            elif isinstance(node, ast.Call):
                call_name = self._expr_name(node.func)
                if call_name:
                    info.function_calls.append(call_name)
                    lowered = call_name.lower()
                    if lowered in {"uvicorn.run", "app.run", "run"} or lowered.endswith(".run"):
                        info.has_app_run = True
                    if any(signal in lowered for signal in ["typer.run", "click.command", "argparse"]):
                        info.has_cli_signal = True
                    self._register_side_effect_call(info, lowered)
            elif isinstance(node, ast.If):
                if self._is_main_guard(node):
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

    def _is_main_guard(self, node: ast.If) -> bool:
        test = node.test
        if not isinstance(test, ast.Compare):
            return False
        if not isinstance(test.left, ast.Name) or test.left.id != "__name__":
            return False
        if not test.comparators:
            return False
        comparator = test.comparators[0]
        return isinstance(comparator, ast.Constant) and comparator.value == "__main__"

    def _register_side_effect_import(self, info: FileInfo, module_name: str) -> None:
        root_module = module_name.split(".")[0].lower()
        category = SIDE_EFFECT_IMPORT_CATEGORIES.get(root_module)
        if category is not None:
            self._add_side_effect(info, category)

    def _register_side_effect_call(self, info: FileInfo, call_name: str) -> None:
        for prefix, category in SIDE_EFFECT_CALL_PREFIXES.items():
            if call_name == prefix or call_name.startswith(prefix):
                self._add_side_effect(info, category)

    def _add_side_effect(self, info: FileInfo, category: str) -> None:
        if category not in info.side_effects:
            info.side_effects.append(category)
        info.has_side_effects = True
