"""Tests for POST /validate and POST /impact/reanalyze contracts."""

from app.models.common import EvidenceSnippet, VerificationStatus


def test_reanalyze_verified(client, sample_impact_input):
    """Test re-analysis verifies resolved impact when new evidence shows total.tax."""
    new_evidence = [
        EvidenceSnippet(
            file="payment.py",
            start_line=87,
            end_line=90,
            content="    total = calculate_total(cart)\n    tax = total.tax\n    subtotal = total.subtotal\n",
            symbol="process_payment",
        )
    ]

    payload = {
        "original_analysis": sample_impact_input.model_dump(),
        "new_evidence": [e.model_dump() for e in new_evidence],
        "test_results": {"passed": True},
    }

    response = client.post("/impact/reanalyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == VerificationStatus.VERIFIED.value
    assert len(data["resolved_issues"]) >= 1
    assert "payment.py:process_payment successfully updated" in data["resolved_issues"][0]


def test_reanalyze_still_affected(client, sample_impact_input):
    """Test re-analysis flags still affected component when old subscript remains."""
    new_evidence = [
        EvidenceSnippet(
            file="payment.py",
            start_line=87,
            end_line=90,
            content="    total = calculate_total(cart)\n    tax = total['tax']\n",
            symbol="process_payment",
        )
    ]

    payload = {
        "original_analysis": sample_impact_input.model_dump(),
        "new_evidence": [e.model_dump() for e in new_evidence],
        "test_results": {"passed": False},
    }

    response = client.post("/validate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == VerificationStatus.STILL_AFFECTED.value
    assert len(data["remaining_issues"]) >= 1
