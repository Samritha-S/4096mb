"""Tests for /ask repository-grounded assistant."""

from app.models.common import EvidenceSnippet


def test_ask_why_affected(client, sample_impact_input):
    """Test developer asking why payment.py is affected receives grounded response."""
    payload = {
        "question": "Why is payment.py affected by the change in cart.py?",
        "project_id": "demo-project",
        "impact_context": sample_impact_input.model_dump(),
        "evidence": [e.model_dump() for e in sample_impact_input.evidence],
    }

    response = client.post("/ask", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert "payment.py" in data["answer"].lower()
    assert len(data["claims"]) >= 1
    assert data["confidence"] in ["HIGH", "MEDIUM"]


def test_ask_fix_intent_attaches_proposal(client, sample_impact_input):
    """Test developer asking 'Fix this issue' triggers intent analysis and attaches fix proposal."""
    cart_total_evidence = EvidenceSnippet(
        file="cart.py",
        start_line=1,
        end_line=5,
        content="class CartTotal:\n    def __init__(self, subtotal, tax):\n        self.tax = tax\n",
        symbol="CartTotal",
    )
    all_evidence = sample_impact_input.evidence + [cart_total_evidence]

    payload = {
        "question": "Fix this issue in payment.py so it uses CartTotal attributes.",
        "project_id": "demo-project",
        "impact_context": sample_impact_input.model_dump(),
        "evidence": [e.model_dump() for e in all_evidence],
    }

    response = client.post("/ask", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert data["fix_proposal"] is not None
    assert data["fix_proposal"]["status"] == "PROPOSED"
    assert len(data["fix_proposal"]["changes"]) >= 1


def test_ask_insufficient_evidence(client):
    """Test developer question without evidence results in low confidence and uncertainties."""
    payload = {
        "question": "Does database.py have any locks on the user table?",
        "project_id": "demo-project",
        "evidence": [],
    }

    response = client.post("/ask", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
