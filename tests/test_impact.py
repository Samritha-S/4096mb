"""Tests for /impact/explain and /impact/verify endpoints."""

def test_impact_explain_success(client, sample_impact_input):
    """Test successful impact explanation with sample analyzer payload."""
    payload = sample_impact_input.model_dump()
    response = client.post("/impact/explain", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert "summary" in data
    assert "risk" in data
    assert data["risk"]["level"] in ["HIGH", "CRITICAL"]
    assert "reason" in data["risk"]
    assert data["impact_type"] == "RETURN_TYPE_CHANGE"

    # Verify Root cause
    assert data["root_cause"]["file"] == "cart.py"
    assert data["root_cause"]["line"] == 42

    # Verify Direct impacts
    assert len(data["direct_impacts"]) >= 1
    assert data["direct_impacts"][0]["file"] == "payment.py"

    # Verify Claims and confidence
    assert len(data["claims"]) >= 1
    assert data["confidence"] in ["HIGH", "MEDIUM"]


def test_impact_explain_missing_change_error(client):
    """Test that missing required 'change' field returns 422 validation error."""
    response = client.post("/impact/explain", json={"project_id": "test-project"})
    assert response.status_code == 422


def test_impact_explain_empty_evidence(client, sample_impact_input):
    """Test that empty evidence produces uncertainties or low confidence."""
    payload = sample_impact_input.model_dump()
    payload["evidence"] = []
    response = client.post("/impact/explain", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert len(data["uncertainties"]) >= 1


def test_impact_verify_citations(client, sample_impact_input):
    """Test /impact/verify endpoint verifying real and hallucinated citations."""
    payload = {
        "citations": [
            {
                "file": "payment.py",
                "start_line": 87,
                "end_line": 90,
                "snippet": "tax = total['tax']",
            },
            {
                "file": "nonexistent.py",
                "start_line": 10,
                "end_line": 20,
            },
        ],
        "evidence": [e.model_dump() for e in sample_impact_input.evidence],
    }

    response = client.post("/impact/verify", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["total_citations"] == 2
    assert data["verified_count"] == 1
    assert data["unverified_count"] == 1
    assert data["failed_citations"][0]["file"] == "nonexistent.py"
