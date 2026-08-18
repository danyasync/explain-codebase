from __future__ import annotations

import re
from pathlib import Path

from explain_codebase.models.file_info import FileInfo
from explain_codebase.utils.file_utils import safe_read_text

FROM_SOURCE_RE = re.compile(r"""\bfrom[ \t]+(?:"([^"\r\n]+)"|'([^'\r\n]+)')""")
REQUIRE_RE = re.compile(
    r"""\brequire[ \t]*\([ \t]*(?:"([^"\r\n]+)"|'([^'\r\n]+)')[ \t]*\)"""
)
FUNCTION_DECLARATION_RE = re.compile(r"""\bfunction[ \t]+([A-Za-z_]\w*)""")
CONST_ASSIGNMENT_RE = re.compile(r"""\bconst[ \t]+([A-Za-z_]\w*)[ \t]*=""")
IDENTIFIER_RE = re.compile(r"""[A-Za-z_]\w*""")
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
        content = safe_read_text(path, root_path=root_path)
        relative_path = path.relative_to(root_path).as_posix()
        info = FileInfo(
            path=relative_path,
            language="javascript",
            line_count=len(content.splitlines()),
        )
        code_positions = self._code_positions(content)
        code = "".join(
            character if is_code or character in "\r\n" else " "
            for character, is_code in zip(content, code_positions, strict=True)
        )

        for imported in self._find_imports(content, code_positions):
            info.imports.append(imported)
            info.import_groups.append([imported])
            self._register_side_effect_import(info, imported)

        info.functions.extend(self._find_functions(code))

        info.classes.extend(CLASS_RE.findall(code))
        info.function_calls.extend(CALL_RE.findall(code))
        info.route_handlers.extend(ROUTE_RE.findall(code))

        lowered = code.lower()
        lowered_calls = {call.lower() for call in info.function_calls}
        info.has_app_listen = bool(lowered_calls.intersection({"app.listen", "server.listen"}))
        info.has_create_server = any(
            call == "createserver" or call.endswith(".createserver") for call in lowered_calls
        )
        imported_roots = {imported.lower().split("/", 1)[0] for imported in info.imports}
        info.has_cli_signal = bool(imported_roots.intersection({"commander", "yargs"}) or "process.argv" in lowered)
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

    def _find_imports(self, content: str, code_positions: list[bool] | None = None) -> list[str]:
        imports: list[str] = []
        code_positions = code_positions or self._code_positions(content)
        offset = 0
        for line in content.splitlines(keepends=True):
            matches: list[tuple[int, str]] = []
            stripped = line.lstrip(" \t")
            if stripped.startswith("import") and len(stripped) > len("import"):
                start = len(line) - len(stripped)
                separator = stripped[len("import")]
                if separator in " \t" and code_positions[offset + start]:
                    remainder = stripped[len("import") :].lstrip(" \t")
                    imported = self._static_import_source(remainder)
                    if imported is not None:
                        matches.append((start, imported))

            for match in REQUIRE_RE.finditer(line):
                if code_positions[offset + match.start()]:
                    matches.append((match.start(), match.group(1) or match.group(2)))

            imports.extend(imported for _, imported in sorted(matches, key=lambda item: item[0]))
            offset += len(line)
        return imports

    def _code_positions(self, content: str) -> list[bool]:
        positions = [True] * len(content)
        state = "code"
        escaped = False
        index = 0
        while index < len(content):
            character = content[index]
            following = content[index + 1] if index + 1 < len(content) else ""

            if state == "code":
                if character == "/" and following == "/":
                    positions[index] = positions[index + 1] = False
                    state = "line_comment"
                    index += 2
                    continue
                if character == "/" and following == "*":
                    positions[index] = positions[index + 1] = False
                    state = "block_comment"
                    index += 2
                    continue
                if character in {'"', "'", "`"}:
                    positions[index] = False
                    state = character
                    escaped = False
            elif state == "line_comment":
                positions[index] = False
                if character in "\r\n":
                    state = "code"
            elif state == "block_comment":
                positions[index] = False
                if character == "*" and following == "/":
                    positions[index + 1] = False
                    state = "code"
                    index += 2
                    continue
            else:
                positions[index] = False
                if escaped:
                    escaped = False
                elif character == "\\":
                    escaped = True
                elif character == state:
                    state = "code"
            index += 1
        return positions

    def _static_import_source(self, remainder: str) -> str | None:
        if not remainder:
            return None
        if remainder[0] in {'"', "'"}:
            quote = remainder[0]
            end = remainder.find(quote, 1)
            return remainder[1:end] if end > 1 else None

        match = FROM_SOURCE_RE.search(remainder)
        if match is None:
            return None
        return match.group(1) or match.group(2)

    def _find_functions(self, content: str) -> list[str]:
        matches = [(match.start(), match.group(1)) for match in FUNCTION_DECLARATION_RE.finditer(content)]
        for match in CONST_ASSIGNMENT_RE.finditer(content):
            if self._has_arrow_signature(content, match.end()):
                matches.append((match.start(), match.group(1)))
        return [name for _, name in sorted(matches, key=lambda item: item[0])]

    def _has_arrow_signature(self, content: str, start: int) -> bool:
        position = self._skip_whitespace(content, start)
        async_match = IDENTIFIER_RE.match(content, position)
        if async_match is not None and async_match.group(0) == "async":
            after_async = self._skip_whitespace(content, async_match.end())
            if not content.startswith("=>", after_async):
                if after_async >= len(content):
                    return False
                if after_async == async_match.end() and content[after_async] != "(":
                    return False
                position = after_async

        identifier_match = IDENTIFIER_RE.match(content, position)
        if identifier_match is not None:
            position = identifier_match.end()
        elif position < len(content) and content[position] == "(":
            closing_position = self._scan_parenthesized(content, position)
            if closing_position is None:
                return False
            position = closing_position
        else:
            return False

        position = self._skip_whitespace(content, position)
        if content.startswith("=>", position):
            return True
        if position >= len(content) or content[position] != ":":
            return False
        return self._scan_return_type_for_arrow(content, position + 1)

    def _scan_parenthesized(self, content: str, start: int) -> int | None:
        depth = 0
        quote: str | None = None
        escaped = False
        position = start
        while position < len(content):
            character = content[position]
            if quote is not None:
                if escaped:
                    escaped = False
                elif character == "\\":
                    escaped = True
                elif character == quote:
                    quote = None
            elif character in {'"', "'", "`"}:
                quote = character
            elif character == "(":
                depth += 1
            elif character == ")":
                depth -= 1
                if depth == 0:
                    return position + 1
            elif character == ";" or self._keyword_at(content, position, "const"):
                return None
            position += 1
        return None

    def _scan_return_type_for_arrow(self, content: str, start: int) -> bool:
        opening = {"(": ")", "[": "]", "{": "}"}
        closing = set(opening.values())
        stack: list[str] = []
        quote: str | None = None
        escaped = False
        position = start
        while position < len(content):
            character = content[position]
            if quote is not None:
                if escaped:
                    escaped = False
                elif character == "\\":
                    escaped = True
                elif character == quote:
                    quote = None
                position += 1
                continue
            if character in {'"', "'", "`"}:
                quote = character
            elif not stack and content.startswith("=>", position):
                return True
            elif character in opening:
                stack.append(opening[character])
            elif character in closing:
                if not stack or stack.pop() != character:
                    return False
            elif not stack and (character == ";" or self._keyword_at(content, position, "const")):
                return False
            position += 1
        return False

    def _skip_whitespace(self, content: str, start: int) -> int:
        position = start
        while position < len(content) and content[position].isspace():
            position += 1
        return position

    def _keyword_at(self, content: str, position: int, keyword: str) -> bool:
        if not content.startswith(keyword, position):
            return False
        previous = content[position - 1] if position > 0 else ""
        next_position = position + len(keyword)
        following = content[next_position] if next_position < len(content) else ""
        return (not previous or not (previous.isalnum() or previous == "_")) and (
            not following or not (following.isalnum() or following == "_")
        )

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
