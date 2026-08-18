from __future__ import annotations

import re
from pathlib import PurePath, PurePosixPath

from explain_codebase.models.file_info import FileInfo

TEST_DIRECTORY_NAMES = {"__tests__", "spec", "specs", "test", "tests"}
AUXILIARY_DIRECTORY_NAMES = TEST_DIRECTORY_NAMES | {
    "example",
    "examples",
    "fixture",
    "fixtures",
}


def source_name_tokens(path: str | PurePath) -> set[str]:
    stem = PurePosixPath(str(path).replace("\\", "/")).stem
    separated = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", stem)
    tokens = {token.lower() for token in re.findall(r"[A-Za-z0-9]+", separated)}
    normalized = set(tokens)
    for token in tokens:
        if token.endswith("ies") and len(token) > 3:
            normalized.add(f"{token[:-3]}y")
        elif token.endswith("s") and len(token) > 1:
            normalized.add(token[:-1])
    return normalized


def is_test_source_path(path: str | PurePath) -> bool:
    normalized = PurePosixPath(str(path).replace("\\", "/"))
    directories = {part.lower() for part in normalized.parts[:-1]}
    return bool(directories.intersection(TEST_DIRECTORY_NAMES) or source_name_tokens(normalized).intersection({"spec", "test"}))


def is_auxiliary_source_path(path: str | PurePath) -> bool:
    normalized = PurePosixPath(str(path).replace("\\", "/"))
    directories = {part.lower() for part in normalized.parts[:-1]}
    return bool(directories.intersection(AUXILIARY_DIRECTORY_NAMES) or is_test_source_path(normalized))


def is_primary_path(path: str | PurePath, role: str | None = None) -> bool:
    return role != "test" and not is_auxiliary_source_path(path)


def is_primary_source(file_info: FileInfo) -> bool:
    """Return whether a file should contribute to the default project rankings."""
    return is_primary_path(file_info.path, file_info.role)
