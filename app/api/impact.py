"""Impact explanation and citation verification endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from app.llm.base import LLMProvider
from app.llm.factory import get_llm_provider
from app.models.requests import ImpactAnalysisInput, VerifyCitationRequest
from app.models.responses import (
    CitationVerificationResult,
    ImpactExplanationResponse,
)
from app.reasoning.claim_verifier import ClaimVerifier
from app.reasoning.impact_engine import ImpactEngine
from app.utils.logging import logger

router = APIRouter()


@router.post("/explain", response_model=ImpactExplanationResponse)
async def explain_impact(
    payload: ImpactAnalysisInput,
    llm: LLMProvider = Depends(get_llm_provider),
) -> ImpactExplanationResponse:
    """Analyze change context from Person 2 (Analyzer) and explain why it matters."""
    logger.info(f"Received impact explanation request for project: '{payload.project_id}'")
    engine = ImpactEngine(llm_provider=llm)
    response = await engine.explain(payload)
    return response


@router.post("/verify", response_model=CitationVerificationResult)
async def verify_citations(
    payload: VerifyCitationRequest,
) -> CitationVerificationResult:
    """Deterministically verify citations against supplied evidence snippets."""
    logger.info(f"Verifying {len(payload.citations)} citation(s) against {len(payload.evidence)} evidence snippet(s).")
    result = ClaimVerifier.verify_all_citations(payload.citations, payload.evidence)
    return result
