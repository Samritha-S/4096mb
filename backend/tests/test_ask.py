from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_ask_returns_answer_and_citations() -> None:
    response = client.post(
        "/ask",
        json={"question": "What is the repository about?", "max_results": 1},
    )

    assert response.status_code == 200
    payload = response.json()
    assert "answer" in payload
    assert isinstance(payload["answer"], str)
    assert "citations" in payload
