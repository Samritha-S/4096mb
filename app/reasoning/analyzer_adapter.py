"""Adapter and Normalization Layer for Person 2's Analyzer Output."""

from typing import Any, Dict, Union
from app.models.common import EvidenceSnippet
from app.models.requests import (
    ChangeDetail,
    ImpactAnalysisInput,
    ImpactedComponent,
)
from app.utils.logging import logger


class AnalyzerAdapter:
    """Normalizes variations in Person 2's analyzer payload into standard ImpactAnalysisInput."""

    @classmethod
    def normalize(cls, raw_data: Union[ImpactAnalysisInput, Dict[str, Any]]) -> ImpactAnalysisInput:
        """Convert arbitrary analyzer dictionary or model into strict ImpactAnalysisInput."""
        if isinstance(raw_data, ImpactAnalysisInput):
            return raw_data

        if not isinstance(raw_data, dict):
            raise ValueError("Analyzer payload must be a JSON object or dictionary.")

        # 1. Project ID
        project_id = raw_data.get("project_id") or raw_data.get("repo_id") or "demo-project"

        # 2. Change Detail
        raw_change = raw_data.get("change") or raw_data.get("code_change") or {}
        change_detail = ChangeDetail(
            file=raw_change.get("file", "unknown.py"),
            start_line=raw_change.get("start_line", 1),
            end_line=raw_change.get("end_line", 1),
            symbol=raw_change.get("symbol"),
            change_type=raw_change.get("change_type", "UNKNOWN"),
            description=raw_change.get("description"),
            before=raw_change.get("before"),
            after=raw_change.get("after"),
        )

        # 3. Impacted components
        raw_impacted = (
            raw_data.get("impacted_components")
            or raw_data.get("affected_components")
            or raw_data.get("callers")
            or []
        )
        impacted_components = []
        for item in raw_impacted:
            if isinstance(item, dict):
                impacted_components.append(
                    ImpactedComponent(
                        file=item.get("file", "unknown.py"),
                        start_line=item.get("start_line", 1),
                        end_line=item.get("end_line", 1),
                        symbol=item.get("symbol"),
                        relationship=item.get("relationship", "calls"),
                        details=item.get("details"),
                    )
                )

        # 4. Impact chain
        raw_chain = (
            raw_data.get("impact_chain")
            or raw_data.get("call_chain")
            or raw_data.get("dependency_chain")
            or []
        )
        impact_chain = [str(node) for node in raw_chain]

        # 5. Evidence snippets
        raw_evidence = (
            raw_data.get("evidence")
            or raw_data.get("snippets")
            or raw_data.get("code_snippets")
            or []
        )
        evidence = []
        for item in raw_evidence:
            if isinstance(item, dict):
                evidence.append(
                    EvidenceSnippet(
                        file=item.get("file", "unknown.py"),
                        start_line=item.get("start_line", 1),
                        end_line=item.get("end_line", 1),
                        content=item.get("content", ""),
                        symbol=item.get("symbol"),
                    )
                )

        normalized = ImpactAnalysisInput(
            project_id=project_id,
            change=change_detail,
            impacted_components=impacted_components,
            impact_chain=impact_chain,
            evidence=evidence,
        )
        return normalized
