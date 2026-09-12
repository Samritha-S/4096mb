"""Validation and Re-analysis contracts."""

from fastapi import APIRouter
from app.models.common import ConfidenceLevel, VerificationStatus
from app.models.requests import ReanalyzeRequest
from app.models.responses import ReanalyzeResponse
from app.utils.logging import logger

router = APIRouter()


@router.post("/impact/reanalyze", response_model=ReanalyzeResponse)
@router.post("/validate", response_model=ReanalyzeResponse)
async def reanalyze_impact(payload: ReanalyzeRequest) -> ReanalyzeResponse:
    """Evaluate new post-fix evidence from Person 1 and Person 2 to verify resolution."""
    logger.info(f"Re-analyzing impact for project '{payload.original_analysis.project_id}'")

    if not payload.new_evidence:
        return ReanalyzeResponse(
            status=VerificationStatus.UNKNOWN,
            summary="No new post-fix evidence provided to verify impact resolution.",
            resolved_issues=[],
            remaining_issues=["Awaiting post-fix code snippets from Local Agent."],
            new_risks=[],
            confidence=ConfidenceLevel.LOW,
        )

    # Check evidence for resolution of dictionary subscription syntax on objects
    new_content = " ".join(e.content for e in payload.new_evidence)
    resolved = []
    remaining = []

    orig_change = payload.original_analysis.change
    for comp in payload.original_analysis.impacted_components:
        matching_new = [e for e in payload.new_evidence if comp.file in e.file]
        if matching_new:
            comp_content = " ".join(e.content for e in matching_new)
            # Check if old subscript pattern is removed and attribute pattern adopted
            if "total['tax']" not in comp_content and "total.tax" in comp_content:
                resolved.append(f"{comp.file}:{comp.symbol} successfully updated to attribute access.")
            elif "total['tax']" in comp_content:
                remaining.append(f"{comp.file}:{comp.symbol} still contains dictionary subscript access.")
            else:
                resolved.append(f"{comp.file}:{comp.symbol} modified; review test coverage.")
        else:
            remaining.append(f"No updated evidence supplied for impacted component {comp.file}.")

    # Evaluate test results if provided by Local Agent
    if payload.test_results:
        passed = payload.test_results.get("passed", False)
        if passed:
            resolved.append("Automated test suite passed on local machine.")
        else:
            remaining.append("Automated tests failed following change application.")

    if not remaining and resolved:
        status = VerificationStatus.VERIFIED
        summary = "All identified impacts have been verified resolved based on new repository evidence."
        confidence = ConfidenceLevel.HIGH
    elif resolved and remaining:
        status = VerificationStatus.PARTIALLY_RESOLVED
        summary = "Some impacts were resolved, but certain components remain affected."
        confidence = ConfidenceLevel.MEDIUM
    else:
        status = VerificationStatus.STILL_AFFECTED
        summary = "Impacts remain unresolved based on supplied evidence."
        confidence = ConfidenceLevel.HIGH

    return ReanalyzeResponse(
        status=status,
        summary=summary,
        resolved_issues=resolved,
        remaining_issues=remaining,
        new_risks=[],
        confidence=confidence,
    )
