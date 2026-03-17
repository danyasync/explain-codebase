from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


Language = Literal["python", "javascript", "typescript", "unknown"]


class FileInfo(BaseModel):
    path: str
    language: Language = "unknown"
    imports: list[str] = Field(default_factory=list)
    functions: list[str] = Field(default_factory=list)
    classes: list[str] = Field(default_factory=list)
    decorators: list[str] = Field(default_factory=list)
    route_handlers: list[str] = Field(default_factory=list)
    function_calls: list[str] = Field(default_factory=list)
    role: str | None = None
    has_main_guard: bool = False
    has_app_run: bool = False
    has_app_listen: bool = False
    has_create_server: bool = False
    has_cli_signal: bool = False
    has_side_effects: bool = False
    line_count: int = 0
    side_effects: list[str] = Field(default_factory=list)
