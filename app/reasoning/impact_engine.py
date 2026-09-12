"""Master Orchestration Engine for Impact Explanation."""

from typing import Any, Dict, List, Union
from app.llm.base import LLMProvider
from app.models.common import (
    Claim,
    CodeCitation,
    ConfidenceLevel,
    EvidenceSnippet,
    ImpactType,
)
from app.models.requests import ImpactAnalysisInput
from app.models.responses import (
    DirectImpact,
    ImpactExplanationResponse,
    IndirectImpact,
    RiskAssessment,
    RootCause,
)
from app.prompts.impact_prompt import (
    IMPACT_SYSTEM_PROMPT,
    format_impact_user_prompt,
)
from app.reasoning.analyzer_adapter import AnalyzerAdapter
from app.reasoning.claim_verifier import ClaimVerifier
from app.reasoning.risk_engine import RiskEngine
from app.utils.logging import logger


class ImpactEngine:
    """Coordinates LLM reasoning, deterministic claim verification, and risk engine evaluation."""

    def __init__(self, llm_provider: LLMProvider):
        self.llm = llm_provider

    async def explain(
        self, raw_input: Union[ImpactAnalysisInput, Dict[str, Any]]
    ) -> ImpactExplanationResponse:
        """Run full impact explanation pipeline."""
        # 1. Normalize input from Person 2
        analysis_input = AnalyzerAdapter.normalize(raw_input)

        # 2. Run deterministic risk evaluation
        deterministic_risk = RiskEngine.evaluate(analysis_input)

        # 3. Query LLM provider for structured reasoning
        user_prompt = format_impact_user_prompt(analysis_input)
        raw_reasoning = await self.llm.generate_structured(
            prompt=user_prompt,
            system_prompt=IMPACT_SYSTEM_PROMPT,
        )

        # 4. Extract and verify claims and citations
        raw_claims = raw_reasoning.get("claims", [])
        parsed_claims: List[Claim] = []
        for c in raw_claims:
            if isinstance(c, dict):
                citations = [
                    CodeCitation(**cit) if isinstance(cit, dict) else cit
                    for cit in c.get("citations", [])
                ]
                parsed_claims.append(
                    Claim(
                        statement=c.get("statement", ""),
                        category=c.get("category", "INFERENCE"),
                        citations=citations,
                        notes=c.get("notes"),
                    )
                )

        # Deterministic verification of claims
        verified_claims = ClaimVerifier.verify_claims(parsed_claims, analysis_input.evidence)

        # 5. Extract Root Cause
        raw_rc = raw_reasoning.get("root_cause", {})
        rc_citations = [
            CodeCitation(**cit) if isinstance(cit, dict) else cit
            for cit in raw_rc.get("citations", [])
        ]
        for cit in rc_citations:
            ClaimVerifier.verify_citation(cit, analysis_input.evidence)

        root_cause = RootCause(
            file=raw_rc.get("file", analysis_input.change.file),
            line=raw_rc.get("line", analysis_input.change.start_line),
            symbol=raw_rc.get("symbol", analysis_input.change.symbol),
            reason=raw_rc.get(
                "reason",
                f"Change in {analysis_input.change.file}:{analysis_input.change.start_line} triggered interface incompatibility.",
            ),
            citations=rc_citations,
        )

        # 6. Extract Direct Impacts
        raw_direct = raw_reasoning.get("direct_impacts", [])
        direct_impacts: List[DirectImpact] = []
        for d in raw_direct:
            if isinstance(d, dict):
                d_citations = [
                    CodeCitation(**cit) if isinstance(cit, dict) else cit
                    for cit in d.get("citations", [])
                ]
                for cit in d_citations:
                    ClaimVerifier.verify_citation(cit, analysis_input.evidence)

                direct_impacts.append(
                    DirectImpact(
                        file=d.get("file", "unknown.py"),
                        symbol=d.get("symbol"),
                        line_range=d.get("line_range"),
                        reason=d.get("reason", "Directly depends on modified component."),
                        citations=d_citations,
                    )
                )

        # If LLM didn't produce direct impacts but analyzer did, populate from analyzer
        if not direct_impacts and analysis_input.impacted_components:
            for comp in analysis_input.impacted_components:
                direct_impacts.append(
                    DirectImpact(
                        file=comp.file,
                        symbol=comp.symbol,
                        line_range=f"{comp.start_line}-{comp.end_line}",
                        reason=f"Impacted via relationship '{comp.relationship}'.",
                        citations=[],
                    )
                )

        # 7. Extract Indirect Impacts
        raw_indirect = raw_reasoning.get("indirect_impacts", [])
        indirect_impacts: List[IndirectImpact] = []
        for ind in raw_indirect:
            if isinstance(ind, dict):
                ind_citations = [
                    CodeCitation(**cit) if isinstance(cit, dict) else cit
                    for cit in ind.get("citations", [])
                ]
                for cit in ind_citations:
                    ClaimVerifier.verify_citation(cit, analysis_input.evidence)

                indirect_impacts.append(
                    IndirectImpact(
                        file=ind.get("file", "unknown.py"),
                        symbol=ind.get("symbol"),
                        reason=ind.get("reason", "Transitively affected component."),
                        path=ind.get("path", []),
                        citations=ind_citations,
                    )
                )

        # 8. Impact Chain
        impact_chain = raw_reasoning.get("impact_chain") or analysis_input.impact_chain

        # 9. Recommendations & Uncertainties
        recommended_actions = raw_reasoning.get("recommended_actions", [])
        uncertainties = raw_reasoning.get("uncertainties", [])

        # If evidence was sparse, document uncertainty
        if not analysis_input.evidence:
            uncertainties.append("No repository evidence snippets were supplied; inferences cannot be verified.")

        # 10. Calculate Overall Confidence
        total_citations = sum(len(c.citations) for c in verified_claims) + len(root_cause.citations)
        verified_citations = (
            sum(1 for c in verified_claims for cit in c.citations if cit.verified)
            + sum(1 for cit in root_cause.citations if cit.verified)
        )

        if total_citations > 0:
            pass_ratio = verified_citations / total_citations
        else:
            pass_ratio = 0.5 if analysis_input.evidence else 0.2

        if pass_ratio >= 0.8 and not uncertainties:
            confidence = ConfidenceLevel.HIGH
        elif pass_ratio >= 0.5 or (uncertainties and len(uncertainties) <= 2):
            confidence = ConfidenceLevel.MEDIUM
        else:
            confidence = ConfidenceLevel.LOW

        # 11. Final Risk - Merge deterministic risk with any extra factors
        final_risk = deterministic_risk
        if "risk" in raw_reasoning and isinstance(raw_reasoning["risk"], dict):
            extra_factors = raw_reasoning["risk"].get("factors", [])
            for f in extra_factors:
                if f not in final_risk.factors:
                    final_risk.factors.append(f)

        return ImpactExplanationResponse(
            summary=raw_reasoning.get(
                "summary",
                f"Change in {analysis_input.change.file} affects {len(direct_impacts)} downstream component(s).",
            ),
            risk=final_risk,
            impact_type=analysis_input.change.change_type or raw_reasoning.get("impact_type", "UNKNOWN"),
            root_cause=root_cause,
            direct_impacts=direct_impacts,
            indirect_impacts=indirect_impacts,
            impact_chain=impact_chain,
            claims=verified_claims,
            recommended_actions=recommended_actions,
            confidence=confidence,
            uncertainties=uncertainties,
        )
