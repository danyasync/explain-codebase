from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from explain_codebase.models.file_info import FileInfo


class ProjectInfo(BaseModel):
    root_path: Path
    files: list[FileInfo] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    project_type: str = "unknown"
