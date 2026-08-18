from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from explain_codebase.models.file_info import FileInfo


class ProjectInfo(BaseModel):
    root_path: Path
    files: list[FileInfo] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    project_type: str = "unknown"
    truncated: bool = False
    discovered_files: int = Field(default=0, ge=0)
    skipped_files: int = Field(default=0, ge=0)
    parse_errors: int = Field(default=0, ge=0)
    unresolved_imports: int = Field(default=0, ge=0)
