from __future__ import annotations

from pydantic import BaseModel, Field


class RankedModule(BaseModel):
    path: str
    score: int


class LargeFileRecord(BaseModel):
    path: str
    loc: int


class HotspotRecord(BaseModel):
    path: str
    incoming_imports: int
    outgoing_imports: int
    coupling_score: int


class ArchitectureIssue(BaseModel):
    issue_type: str
    description: str
    affected_paths: list[str] = Field(default_factory=list)


class FileExplanation(BaseModel):
    path: str
    role: str
    used_by: list[str] = Field(default_factory=list)
    depends_on: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    line_count: int = 0
    incoming_imports: int = 0
    outgoing_imports: int = 0
    side_effects: list[str] = Field(default_factory=list)


class AnalysisResult(BaseModel):
    project_root: str
    project_type: str
    languages: list[str] = Field(default_factory=list)
    total_files: int
    entrypoints: list[str] = Field(default_factory=list)
    core_modules: list[str] = Field(default_factory=list)
    core_module_rankings: list[RankedModule] = Field(default_factory=list)
    side_effect_modules: list[str] = Field(default_factory=list)
    architecture_modules: list[str] = Field(default_factory=list)
    large_files: list[LargeFileRecord] = Field(default_factory=list)
    hotspots: list[HotspotRecord] = Field(default_factory=list)
    dangerous_files: list[str] = Field(default_factory=list)
    architecture_issues: list[ArchitectureIssue] = Field(default_factory=list)
    execution_flow: list[list[str]] = Field(default_factory=list)
    file_roles: dict[str, str] = Field(default_factory=dict)
    centrality: dict[str, int] = Field(default_factory=dict)
    dependency_graph_output: str | None = None
    html_report_output: str | None = None
    summary: str
