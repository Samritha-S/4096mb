"""Pydantic request contracts for Person 2 (Analyzer) and Person 4 (Frontend)."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.models.common import (
    CodeCitation,
    EvidenceSnippet,
    ImpactType,
)


class ChangeDetail(BaseModel):
    """Details of the source code modification triggering the analysis."""
    file: str = Field(..., description="File path where change occurred")
    start_line: int = Field(..., ge=1, description="Starting line of the change")
    end_line: int = Field(..., ge=1, description="Ending line of the change")
    symbol: Optional[str] = Field(None, description="Modified symbol name")
    change_type: str = Field(
        default=ImpactType.UNKNOWN.value,
        description="Type of code change (e.g. RETURN_TYPE_CHANGE, SIGNATURE_CHANGE)",
    )
    description: Optional[str] = Field(None, description="Human or analyzer description of change")
    before: Optional[str] = Field(None, description="Code snippet before the change")
    after: Optional[str] = Field(None, description="Code snippet after the change")


class ImpactedComponent(BaseModel):
    """Component identified by Person 2's analyzer as affected."""
    file: str = Field(..., description="File path of impacted component")
    start_line: int = Field(..., ge=1, description="Start line in impacted file")
    end_line: int = Field(..., ge=1, description="End line in impacted file")
    symbol: Optional[str] = Field(None, description="Impacted symbol name")
    relationship: str = Field(
        default="calls",
        description="Dependency relationship: 'calls', 'imports', 'inherits', 'references'",
    )
    details: Optional[str] = Field(None, description="Additional context on the relationship")


class ImpactAnalysisInput(BaseModel):
    """Primary input contract from Person 2 (Analyzer)."""
    project_id: Optional[str] = Field(default="demo-project", description="Project identifier")
    change: ChangeDetail = Field(..., description="Primary code change")
    impacted_components: List[ImpactedComponent] = Field(
        default_factory=list, description="Downstream components directly or indirectly impacted"
    )
    impact_chain: List[str] = Field(
        default_factory=list, description="Ordered dependency/call chain, e.g. ['cart.py:funcA', 'payment.py:funcB']"
    )
    evidence: List[EvidenceSnippet] = Field(
        default_factory=list, description="Concrete code snippets supporting the analysis"
    )


class AskRequest(BaseModel):
    """Input contract for repository-grounded developer assistant."""
    question: str = Field(..., min_length=2, description="Developer's question about the change or impact")
    project_id: Optional[str] = Field(default="demo-project", description="Project identifier")
    impact_context: Optional[ImpactAnalysisInput] = Field(
        None, description="Impact context from Person 2 or previous explanation"
    )
    evidence: List[EvidenceSnippet] = Field(
        default_factory=list, description="Additional evidence snippets if available"
    )
    constraints: List[str] = Field(
        default_factory=list, description="Developer-specified constraints (e.g. 'do not change public API')"
    )


class FixProposalRequest(BaseModel):
    """Strict input contract for safe code-rewrite proposals."""
    instruction: str = Field(
        ..., min_length=3, description="Explicit developer intent specifying what must be fixed"
    )
    constraints: List[str] = Field(
        default_factory=list, description="Strict guidelines (e.g. 'Preserve existing behavior')"
    )
    impact_analysis: ImpactAnalysisInput = Field(
        ..., description="Impact analysis context containing the change and impacted callers"
    )
    evidence: List[EvidenceSnippet] = Field(
        default_factory=list, description="Code snippets showing caller context and type definitions"
    )
    target_file: Optional[str] = Field(
        None, description="Specific file to fix if targeting a single component"
    )


class VerifyCitationRequest(BaseModel):
    """Input contract for deterministic citation verification."""
    citations: List[CodeCitation] = Field(..., description="Citations to check")
    evidence: List[EvidenceSnippet] = Field(..., description="Supplied evidence to verify against")


class ReanalyzeRequest(BaseModel):
    """Input contract for re-analysis after fix application."""
    original_analysis: ImpactAnalysisInput = Field(..., description="Original impact analysis")
    new_evidence: List[EvidenceSnippet] = Field(..., description="Evidence collected post-fix")
    new_change: Optional[ChangeDetail] = Field(None, description="Optional new change description")
    test_results: Optional[Dict[str, Any]] = Field(None, description="Optional test execution output from Local Agent")
