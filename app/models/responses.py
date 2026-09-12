"""Pydantic response contracts consumed by Person 4 (Frontend)."""

from typing import List, Optional
from pydantic import BaseModel, Field

from app.models.common import (
    Claim,
    CodeCitation,
    ConfidenceLevel,
    FixStatus,
    RiskLevel,
    VerificationStatus,
)


class RiskAssessment(BaseModel):
    """Deterministic risk evaluation and supporting rationale."""
    level: RiskLevel = Field(..., description="Overall risk level (LOW, MEDIUM, HIGH, CRITICAL, UNKNOWN)")
    reason: str = Field(..., description="Detailed explanation grounded in evidence")
    factors: List[str] = Field(default_factory=list, description="Specific risk drivers evaluated")


class RootCause(BaseModel):
    """Grounding of where and why the regression or breakage originated."""
    file: str = Field(..., description="File path of the root cause")
    line: int = Field(..., ge=1, description="Line number of root cause")
    symbol: Optional[str] = Field(None, description="Symbol name associated with root cause")
    reason: str = Field(..., description="Explanation of why this is the root cause")
    citations: List[CodeCitation] = Field(default_factory=list, description="Evidence citations")


class DirectImpact(BaseModel):
    """Component directly calling or interfacing with modified code."""
    file: str = Field(..., description="Impacted file path")
    symbol: Optional[str] = Field(None, description="Impacted symbol name")
    line_range: Optional[str] = Field(None, description="Range of affected lines, e.g. '87-90'")
    reason: str = Field(..., description="Concrete reason for breakage")
    citations: List[CodeCitation] = Field(default_factory=list, description="Evidence citations")


class IndirectImpact(BaseModel):
    """Component transitively impacted through callers or dependencies."""
    file: str = Field(..., description="Indirectly impacted file path")
    symbol: Optional[str] = Field(None, description="Impacted symbol name")
    reason: str = Field(..., description="Explanation of indirect effect")
    path: List[str] = Field(default_factory=list, description="Path through dependency graph")
    citations: List[CodeCitation] = Field(default_factory=list, description="Evidence citations")


class ImpactExplanationResponse(BaseModel):
    """Complete semantic explanation returned to Person 4."""
    summary: str = Field(..., description="Executive summary of the change impact")
    risk: RiskAssessment = Field(..., description="Deterministic risk assessment")
    impact_type: str = Field(..., description="Primary impact classification")
    root_cause: RootCause = Field(..., description="Identified root cause")
    direct_impacts: List[DirectImpact] = Field(default_factory=list, description="Directly impacted callers")
    indirect_impacts: List[IndirectImpact] = Field(default_factory=list, description="Transitively impacted callers")
    impact_chain: List[str] = Field(default_factory=list, description="Ordered dependency/call chain")
    claims: List[Claim] = Field(default_factory=list, description="Grounding claims (Fact/Inference/Assumption)")
    recommended_actions: List[str] = Field(default_factory=list, description="Concrete next steps for developer")
    confidence: ConfidenceLevel = Field(..., description="Confidence score based on evidence completeness")
    uncertainties: List[str] = Field(default_factory=list, description="Information gaps or missing evidence")


class FixChange(BaseModel):
    """Single file replacement chunk in a proposed fix."""
    file: str = Field(..., description="File to modify")
    start_line: int = Field(..., ge=1, description="Start line of replacement chunk")
    end_line: int = Field(..., ge=1, description="End line of replacement chunk")
    old_code: str = Field(..., description="Exact existing code to replace")
    new_code: str = Field(..., description="Proposed safe replacement code")
    reason: str = Field(..., description="Why this exact replacement is correct")
    citations: List[CodeCitation] = Field(default_factory=list, description="Citations supporting the rewrite")


class FixProposalResponse(BaseModel):
    """Non-destructive fix proposal for developer review."""
    status: FixStatus = Field(..., description="PROPOSED, NEEDS_CLARIFICATION, or NEEDS_MORE_EVIDENCE")
    summary: str = Field(..., description="Overview of the proposed fix")
    changes: List[FixChange] = Field(default_factory=list, description="Proposed code changes")
    diff: Optional[str] = Field(None, description="Unified diff representation")
    assumptions: List[str] = Field(default_factory=list, description="Explicit assumptions if any")
    uncertainties: List[str] = Field(default_factory=list, description="Uncertainties or unverified behaviors")
    confidence: ConfidenceLevel = Field(..., description="Confidence level in the proposed fix")
    message: Optional[str] = Field(None, description="Guidance message if clarification/evidence is needed")


class AskResponse(BaseModel):
    """Grounded response to developer Q&A."""
    answer: str = Field(..., description="Answer to the developer's question")
    claims: List[Claim] = Field(default_factory=list, description="Grounding claims")
    citations: List[CodeCitation] = Field(default_factory=list, description="Referenced code locations")
    recommended_actions: List[str] = Field(default_factory=list, description="Action items")
    confidence: ConfidenceLevel = Field(..., description="Confidence level in the response")
    uncertainties: List[str] = Field(default_factory=list, description="Uncertainties identified")
    fix_proposal: Optional[FixProposalResponse] = Field(None, description="Attached fix proposal if requested")


class CitationVerificationResult(BaseModel):
    """Deterministic result of citation verification."""
    total_citations: int
    verified_count: int
    unverified_count: int
    verified_citations: List[CodeCitation]
    failed_citations: List[CodeCitation]
    summary: str


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "ok"
    version: str = "1.0.0"
    demo_mode: bool
    llm_provider: str
    model: str


class ReanalyzeResponse(BaseModel):
    """Verification of whether a fix resolved the impacts."""
    status: VerificationStatus
    summary: str
    resolved_issues: List[str] = Field(default_factory=list)
    remaining_issues: List[str] = Field(default_factory=list)
    new_risks: List[str] = Field(default_factory=list)
    confidence: ConfidenceLevel
