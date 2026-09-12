"""Fix proposal and safe modification endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from app.llm.base import LLMProvider
from app.llm.factory import get_llm_provider
from app.models.requests import FixProposalRequest
from app.models.responses import FixProposalResponse
from app.prompts.fix_prompt import FIX_SYSTEM_PROMPT, format_fix_user_prompt
from app.reasoning.fix_engine import FixEngine
from app.utils.logging import logger

router = APIRouter()


@router.post("/propose", response_model=FixProposalResponse)
async def propose_fix(
    payload: FixProposalRequest,
    llm: LLMProvider = Depends(get_llm_provider),
) -> FixProposalResponse:
    """Generate a safe, evidence-grounded fix proposal with unified diff."""
    logger.info(f"Received fix proposal request with instruction: '{payload.instruction}'")

    prompt = format_fix_user_prompt(payload)
    raw_fix = await llm.generate_structured(
        prompt=prompt,
        system_prompt=FIX_SYSTEM_PROMPT,
    )

    proposal = FixEngine.evaluate_and_build_proposal(payload, raw_fix)
    return proposal


@router.post("/apply")
async def apply_fix():
    """Architectural contract: Local file modification is performed by Person 1's Local Agent."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
            "code": "FILESYSTEM_ACCESS_RESTRICTED",
            "message": (
                "The backend is client-agnostic and does NOT directly modify local files on disk. "
                "In CodeImpact's architecture, file modifications must be applied locally by Person 1's "
                "Local Agent following explicit developer approval."
            ),
            "expected_actor": "Person 1 (Local Agent)",
        },
    )
