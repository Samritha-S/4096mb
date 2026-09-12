"""Tests for Fix Proposal Engine and Unified Diff Generation."""

from app.models.common import EvidenceSnippet, FixStatus
from app.models.requests import FixProposalRequest
from app.reasoning.fix_engine import FixEngine


def test_fix_propose_success(client, sample_impact_input):
    """Test safe fix proposal with verified CartTotal attribute evidence."""
    cart_total_evidence = EvidenceSnippet(
        file="cart.py",
        start_line=1,
        end_line=5,
        content="class CartTotal:\n    def __init__(self, subtotal, tax):\n        self.tax = tax\n",
        symbol="CartTotal",
    )
    all_evidence = sample_impact_input.evidence + [cart_total_evidence]

    payload = {
        "instruction": "Fix payment.py caller to access tax attribute on CartTotal instead of dictionary subscript.",
        "constraints": ["Do not alter process_payment signature", "Preserve existing tax calculation"],
        "target_file": "payment.py",
        "impact_analysis": sample_impact_input.model_dump(),
        "evidence": [e.model_dump() for e in all_evidence],
    }

    response = client.post("/fix/propose", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "PROPOSED"
    assert len(data["changes"]) >= 1
    assert data["changes"][0]["file"] == "payment.py"
    assert "tax = total.tax" in data["changes"][0]["new_code"]
    assert data["diff"] is not None
    assert "--- a/payment.py" in data["diff"]
    assert "+++ b/payment.py" in data["diff"]


def test_fix_propose_ambiguous_instruction(client, sample_impact_input):
    """Test ambiguous instructions produce NEEDS_CLARIFICATION without guessing."""
    payload = {
        "instruction": "fix",
        "constraints": [],
        "impact_analysis": sample_impact_input.model_dump(),
        "evidence": [e.model_dump() for e in sample_impact_input.evidence],
    }

    response = client.post("/fix/propose", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "NEEDS_CLARIFICATION"
    assert len(data["changes"]) == 0
    assert data["diff"] is None


def test_fix_propose_insufficient_evidence(client, sample_impact_input):
    """Test missing CartTotal definition produces NEEDS_MORE_EVIDENCE."""
    # Only supply caller evidence, omitting CartTotal class definition
    payload = {
        "instruction": "Fix payment.py to work with new return type without assuming attributes.",
        "constraints": [],
        "impact_analysis": sample_impact_input.model_dump(),
        "evidence": [sample_impact_input.evidence[1].model_dump()],  # Only payment.py
    }

    response = client.post("/fix/propose", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "NEEDS_MORE_EVIDENCE"
    assert len(data["uncertainties"]) >= 1


def test_fix_apply_restricted(client):
    """Test that POST /fix/apply is restricted to prevent unsafe filesystem modification."""
    response = client.post("/fix/apply")
    assert response.status_code == 501
    data = response.json()
    assert "detail" in data
    assert data["detail"]["code"] == "FILESYSTEM_ACCESS_RESTRICTED"


def test_diff_generation_utility():
    """Test that unified diff generation produces standard git-compatible diffs."""
    old_code = "tax = total['tax']"
    new_code = "tax = total.tax"
    diff = FixEngine.generate_unified_diff("payment.py", old_code, new_code, 89)

    assert "--- a/payment.py" in diff
    assert "+++ b/payment.py" in diff
    assert "-tax = total['tax']" in diff
    assert "+tax = total.tax" in diff
