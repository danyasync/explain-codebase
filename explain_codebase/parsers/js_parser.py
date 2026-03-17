from __future__ import annotations

import re
from pathlib import Path

from explain_codebase.models.file_info import FileInfo
from explain_codebase.utils.file_utils import safe_read_text


IMPORT_RE = re.compile(r"""import\s+(?:.+?\s+from\s+)?["'](.+?)["']|require\(["'](.+?)["']\)""")
FUNCTION_RE = re.compile(r"""(?:function\s+([A-Za-z_]\w*)|\bconst\s+([A-Za-z_]\w*)\s*=\s*\(?[^=]*?\)?\s*=>)""")
CLASS_RE = re.compile(r"""\bclass\s+([A-Za-z_]\w*)""")
CALL_RE = re.compile(r"""\b([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*)\s*\(""")
ROUTE_RE = re.compile(r"""\b(?:app|router)\.(get|post|put|delete|patch|use)\s*\(""")

SIDE_EFFECT_IMPORT_CATEGORIES = {
    "axios": "network",
    "aiohttp": "network",
    "fs": "filesystem",
    "http": "network",
    "https": "network",
    "ioredis": "cache",
    "mongodb": "database",
    "mongoose": "database",
    "mysql": "database",
    "node-fetch": "network",
    "pg": "database",
    "prisma": "database",
    "redis": "cache",
    "sequelize": "database",
}


class JavaScriptParser:
    def parse(self, path: Path, root_path: Path) -> FileInfo:
        content = safe_read_text(path)
        relative_path = path.relative_to(root_path).as_posix()
        info = FileInfo(
            path=relative_path,
            language="javascript",
            line_count=len(content.splitlines()),
        )

        for first, second in IMPORT_RE.findall(content):
            imported = first or second
            info.imports.append(imported)
            self._register_side_effect_import(info, imported)

        for match in FUNCTION_RE.findall(content):
            name = match[0] or match[1]
            if name:
                info.functions.append(name)

        info.classes.extend(CLASS_RE.findall(content))
        info.function_calls.extend(CALL_RE.findall(content))
        info.route_handlers.extend(ROUTE_RE.findall(content))

        lowered = content.lower()
        info.has_app_listen = "app.listen(" in lowered
        if "server.listen(" in lowered:
            info.has_app_listen = True
        info.has_create_server = "createserver(" in lowered
        info.has_cli_signal = any(signal in lowered for signal in ["commander", "yargs", "process.argv"])
        for keyword, category in {
            "axios.": "network",
            "fetch(": "network",
            "fs.": "filesystem",
            "http.": "network",
            "https.": "network",
            "mongoose": "database",
            "mysql": "database",
            "pg.": "database",
            "prisma": "database",
            "redis": "cache",
            "sequelize": "database",
        }.items():
            if keyword in lowered:
                self._add_side_effect(info, category)
        return info

    def _register_side_effect_import(self, info: FileInfo, module_name: str) -> None:
        cleaned_name = module_name.lower().lstrip("./")
        root_module = cleaned_name.split("/")[0]
        category = SIDE_EFFECT_IMPORT_CATEGORIES.get(root_module)
        if category is not None:
            self._add_side_effect(info, category)

    def _add_side_effect(self, info: FileInfo, category: str) -> None:
        if category not in info.side_effects:
            info.side_effects.append(category)
        info.has_side_effects = True
