from __future__ import annotations

import json

from explain_codebase.models.analysis_result import AnalysisResult


class JsonRenderer:
    def render(self, result: AnalysisResult) -> str:
        return json.dumps(result.model_dump(), indent=2)

    def render_data(self, data: object) -> str:
        return json.dumps(data, indent=2)
