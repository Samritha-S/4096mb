"""Tests for deterministic Risk Engine."""

from app.models.common import EvidenceSnippet, ImpactType, RiskLevel
from app.models.requests import ChangeDetail, ImpactAnalysisInput, ImpactedComponent
from app.reasoning.risk_engine import RiskEngine


def test_risk_unknown_on_insufficient_evidence():
    """Test risk engine returns UNKNOWN when no context or evidence is supplied."""
    inp = ImpactAnalysisInput(
        project_id="test",
        change=ChangeDetail(
            file="unknown.py",
            start_line=1,
            end_line=1,
            change_type="UNKNOWN",
        ),
        impacted_components=[],
        evidence=[],
    )
    risk = RiskEngine.evaluate(inp)
    assert risk.level == RiskLevel.UNKNOWN
    assert "Insufficient evidence" in risk.reason


def test_risk_high_for_breaking_return_type():
    """Test return type change affecting payment caller is evaluated as HIGH."""
    inp = ImpactAnalysisInput(
        project_id="test",
        change=ChangeDetail(
            file="cart.py",
            start_line=42,
            end_line=48,
            symbol="calculate_total",
            change_type=ImpactType.RETURN_TYPE_CHANGE.value,
        ),
        impacted_components=[
            ImpactedComponent(
                file="payment.py",
                start_line=87,
                end_line=90,
                symbol="process_payment",
                relationship="calls",
            )
        ],
        evidence=[
            EvidenceSnippet(
                file="payment.py",
                start_line=87,
                end_line=90,
                content="tax = total['tax']",
            )
        ],
    )
    risk = RiskEngine.evaluate(inp)
    assert risk.level in [RiskLevel.HIGH, RiskLevel.CRITICAL]
    assert len(risk.factors) >= 2


def test_risk_critical_for_database_contract():
    """Test database contract changes trigger CRITICAL risk."""
    inp = ImpactAnalysisInput(
        project_id="test",
        change=ChangeDetail(
            file="models.py",
            start_line=10,
            end_line=20,
            change_type=ImpactType.DATABASE_CONTRACT_CHANGE.value,
            description="Dropped primary key column id",
        ),
        impacted_components=[
            ImpactedComponent(file="repo.py", start_line=1, end_line=10),
            ImpactedComponent(file="service.py", start_line=1, end_line=10),
        ],
        evidence=[
            EvidenceSnippet(file="models.py", start_line=10, end_line=20, content="column dropped")
        ],
    )
    risk = RiskEngine.evaluate(inp)
    assert risk.level == RiskLevel.CRITICAL


def test_risk_low_for_isolated_behavior_change():
    """Test internal behavior change without callers triggers LOW risk."""
    inp = ImpactAnalysisInput(
        project_id="test",
        change=ChangeDetail(
            file="internal_helper.py",
            start_line=5,
            end_line=10,
            change_type=ImpactType.BEHAVIOR_CHANGE.value,
            description="Optimized internal sort algorithm",
        ),
        impacted_components=[],
        evidence=[
            EvidenceSnippet(file="internal_helper.py", start_line=5, end_line=10, content="x.sort()")
        ],
    )
    risk = RiskEngine.evaluate(inp)
    assert risk.level == RiskLevel.LOW
