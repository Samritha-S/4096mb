"""Common data models, enums, and grounding structures."""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
    UNKNOWN = "UNKNOWN"


class ConfidenceLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class ImpactType(str, Enum):
    SIGNATURE_CHANGE = "SIGNATURE_CHANGE"
    RETURN_TYPE_CHANGE = "RETURN_TYPE_CHANGE"
    PARAMETER_CHANGE = "PARAMETER_CHANGE"
    BEHAVIOR_CHANGE = "BEHAVIOR_CHANGE"
    API_CONTRACT_CHANGE = "API_CONTRACT_CHANGE"
    DATABASE_CONTRACT_CHANGE = "DATABASE_CONTRACT_CHANGE"
    DATA_FORMAT_CHANGE = "DATA_FORMAT_CHANGE"
    EXCEPTION_BEHAVIOR_CHANGE = "EXCEPTION_BEHAVIOR_CHANGE"
    AUTHORIZATION_CHANGE = "AUTHORIZATION_CHANGE"
    DEPENDENCY_CHANGE = "DEPENDENCY_CHANGE"
    DIRECT_CALLER_IMPACT = "DIRECT_CALLER_IMPACT"
    INDIRECT_IMPACT = "INDIRECT_IMPACT"
    TEST_IMPACT = "TEST_IMPACT"
    CONFIGURATION_IMPACT = "CONFIGURATION_IMPACT"
    UNKNOWN = "UNKNOWN"


class ClaimCategory(str, Enum):
    """Grounding category strictly distinguishing factual evidence from assumptions."""
    FACT = "FACT"
    INFERENCE = "INFERENCE"
    ASSUMPTION = "ASSUMPTION"
    UNCERTAINTY = "UNCERTAINTY"


class FixStatus(str, Enum):
    PROPOSED = "PROPOSED"
    NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"
    NEEDS_MORE_EVIDENCE = "NEEDS_MORE_EVIDENCE"
    REJECTED = "REJECTED"


class VerificationStatus(str, Enum):
    VERIFIED = "VERIFIED"
    PARTIALLY_RESOLVED = "PARTIALLY_RESOLVED"
    STILL_AFFECTED = "STILL_AFFECTED"
    NEW_IMPACT_DETECTED = "NEW_IMPACT_DETECTED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    UNKNOWN = "UNKNOWN"


class EvidenceSnippet(BaseModel):
    """Code snippet provided as concrete evidence from the repository."""
    file: str = Field(..., description="File path relative to repository root")
    start_line: int = Field(..., ge=1, description="1-based starting line number")
    end_line: int = Field(..., ge=1, description="1-based ending line number")
    content: str = Field(..., description="Exact code contents of the evidence region")
    symbol: Optional[str] = Field(None, description="Enclosing symbol (function, method, class)")


class CodeCitation(BaseModel):
    """Citation linking a claim directly to repository evidence."""
    file: str = Field(..., description="Referenced file path")
    start_line: Optional[int] = Field(None, ge=1, description="Referenced start line")
    end_line: Optional[int] = Field(None, ge=1, description="Referenced end line")
    symbol: Optional[str] = Field(None, description="Referenced symbol")
    snippet: Optional[str] = Field(None, description="Specific cited code line or snippet")
    verified: Optional[bool] = Field(None, description="Whether citation was deterministically verified")
    verification_notes: Optional[str] = Field(None, description="Details on verification check")


class Claim(BaseModel):
    """Grounding claim distinguishing facts, inferences, and uncertainties."""
    statement: str = Field(..., description="Text statement of the claim")
    category: ClaimCategory = Field(..., description="Grounding classification")
    citations: List[CodeCitation] = Field(default_factory=list, description="Evidence citations for this claim")
    verified: bool = Field(default=False, description="True if all citations are verified against evidence")
    notes: Optional[str] = Field(None, description="Reasoning or uncertainty notes")
