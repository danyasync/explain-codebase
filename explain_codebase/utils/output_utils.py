from __future__ import annotations

import os
import tempfile
import unicodedata
from contextlib import suppress
from pathlib import Path


def terminal_safe_text(value: object) -> str:
    """Render terminal control characters as visible escapes."""
    escaped: list[str] = []
    for character in str(value):
        category = unicodedata.category(character)
        if category not in {"Cc", "Cf", "Zl", "Zp"}:
            escaped.append(character)
            continue

        codepoint = ord(character)
        named_escape = {"\n": r"\n", "\r": r"\r", "\t": r"\t"}.get(character)
        if named_escape is not None:
            escaped.append(named_escape)
        elif codepoint <= 0xFF:
            escaped.append(f"\\x{codepoint:02x}")
        elif codepoint <= 0xFFFF:
            escaped.append(f"\\u{codepoint:04x}")
        else:
            escaped.append(f"\\U{codepoint:08x}")
    return "".join(escaped)


def atomic_write_text(output_path: Path, content: str) -> None:
    """Atomically replace output_path without following an existing output symlink."""
    output_path = output_path.absolute()
    parent = output_path.parent
    temporary_path: Path | None = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            prefix=f".{output_path.name}.",
            suffix=".tmp",
            dir=parent,
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            temporary_file.write(content)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())

        os.replace(temporary_path, output_path)
        temporary_path = None
    finally:
        if temporary_path is not None:
            with suppress(OSError):
                temporary_path.unlink(missing_ok=True)
