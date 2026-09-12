"""Deterministic Risk Calculation Engine."""

from typing import List, Optional
from app.models.common import (
    EvidenceSnippet,
    ImpactType,
    RiskLevel,
)
from app.models.requests import ImpactAnalysisInput
from app.models.responses import RiskAssessment


class RiskEngine:
    """Evaluates risk deterministically based on change severity, caller blast radius, and evidence."""

    CRITICAL_CHANGE_TYPES = {
        ImpactType.DATABASE_CONTRACT_CHANGE.value,
        ImpactType.AUTHORIZATION_CHANGE.value,
    }

    HIGH_CHANGE_TYPES = {
        ImpactType.RETURN_TYPE_CHANGE.value,
        ImpactType.SIGNATURE_CHANGE.value,
        ImpactType.API_CONTRACT_CHANGE.value,
        ImpactType.PARAMETER_CHANGE.value,
    }

    SENSITIVE_KEYWORDS = {
        "payment": "Payment transaction and billing path",
        "auth": "Authentication or authorization security boundary",
        "crypto": "Cryptographic or secret processing",
        "database": "Database schema or query contract",
        "order": "Order processing and fulfillment flow",
    }

    @classmethod
    def evaluate(cls, analysis_input: ImpactAnalysisInput) -> RiskAssessment:
        """Calculate deterministic risk level and produce explainable factors."""
        change = analysis_input.change
        callers = analysis_input.impacted_components
        impact_chain = analysis_input.impact_chain
        evidence = analysis_input.evidence

        factors: List[str] = []
        score = 0  # 0-3: LOW, 4-6: MEDIUM, 7-9: HIGH, 10+: CRITICAL

        # 1. Evidence sufficiency check
        if not evidence and not callers and not change.description:
            return RiskAssessment(
                level=RiskLevel.UNKNOWN,
                reason="Insufficient evidence: No code snippets or caller definitions provided to safely evaluate risk.",
                factors=["Zero evidence snippets supplied", "Caller contexts missing"],
            )

        # 2. Change type severity
        change_type = (change.change_type or "").upper()
        if change_type in cls.CRITICAL_CHANGE_TYPES:
            score += 6
            factors.append(f"Critical change type: {change_type} directly modifies database or security contracts.")
        elif change_type in cls.HIGH_CHANGE_TYPES:
            score += 4
            factors.append(f"High-impact change type: {change_type} breaks interface contracts across callers.")
        elif change_type == ImpactType.BEHAVIOR_CHANGE.value:
            score += 2
            factors.append("Behavioral change without contract modification.")
        elif change_type in (ImpactType.TEST_IMPACT.value, ImpactType.CONFIGURATION_IMPACT.value):
            score += 1
            factors.append(f"Localized impact type: {change_type}.")

        # 3. Direct callers blast radius
        num_callers = len(callers)
        if num_callers == 0:
            factors.append("No downstream callers detected by analyzer.")
        elif num_callers == 1:
            score += 2
            factors.append(f"Single downstream caller affected: {callers[0].file}:{callers[0].symbol or 'unknown'}.")
        elif num_callers <= 3:
            score += 3
            factors.append(f"Multiple downstream callers affected ({num_callers} components).")
        else:
            score += 5
            factors.append(f"Broad blast radius: {num_callers} downstream components directly impacted.")

        # 4. Impact chain depth (indirect impacts)
        chain_depth = len(impact_chain)
        if chain_depth > 3:
            score += 2
            factors.append(f"Deep dependency chain ({chain_depth} tiers) propagating through repository.")
        elif chain_depth > 1:
            score += 1
            factors.append(f"Multi-tier call chain detected ({chain_depth} tiers).")

        # 5. Sensitive domain context grounded in evidence
        sensitive_matches = []
        all_text = " ".join(
            [change.file, change.change_type, change.description or ""]
            + [c.file for c in callers]
            + [e.file for e in evidence]
            + [e.content for e in evidence]
        ).lower()

        for kw, desc in cls.SENSITIVE_KEYWORDS.items():
            if kw in all_text:
                sensitive_matches.append(desc)

        if sensitive_matches:
            # Only elevate risk if callers exist and contract changed
            if num_callers > 0 and (change_type in cls.HIGH_CHANGE_TYPES or change_type in cls.CRITICAL_CHANGE_TYPES):
                score += 3
                factors.append(
                    f"Contract change directly intersects with critical domains: {', '.join(sensitive_matches)}."
                )
            else:
                score += 1
                factors.append(f"Relevant domain keywords present in context: {', '.join(sensitive_matches)}.")

        # 6. Syntax or contract mismatch in evidence
        # e.g. caller uses subscript ['...'] while function returns class instance
        evidence_content = " ".join([e.content for e in evidence])
        if change_type == ImpactType.RETURN_TYPE_CHANGE.value:
            if "['" in evidence_content or '["' in evidence_content:
                score += 2
                factors.append("Evidence reveals dictionary subscript access on return type that was changed to an object.")

        # Determine level based on score
        if score >= 9:
            level = RiskLevel.CRITICAL
            reason = (
                f"Critical risk: {change_type} affects {num_callers} caller(s) "
                f"with potential runtime exceptions across sensitive operational paths."
            )
        elif score >= 6:
            level = RiskLevel.HIGH
            reason = (
                f"High risk: {change_type} causes interface incompatibility in {num_callers} downstream caller(s), "
                f"likely resulting in unhandled runtime errors if not adapted."
            )
        elif score >= 3:
            level = RiskLevel.MEDIUM
            reason = (
                f"Medium risk: Change affects {num_callers} caller(s) but blast radius is localized and manageable."
            )
        else:
            level = RiskLevel.LOW
            reason = "Low risk: Change is localized with minimal downstream impact or non-breaking behavior."

        return RiskAssessment(
            level=level,
            reason=reason,
            factors=factors,
        )
