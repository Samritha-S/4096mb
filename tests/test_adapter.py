"""Tests for AnalyzerAdapter and error handling."""

import pytest
from app.reasoning.analyzer_adapter import AnalyzerAdapter
from app.utils.errors import MalformedLLMResponseException


def test_analyzer_adapter_normalization():
    """Test AnalyzerAdapter handles alternative naming keys from Person 2."""
    raw_payload = {
        "repo_id": "alternate-project-id",
        "code_change": {
            "file": "billing.py",
            "start_line": 15,
            "end_line": 20,
            "symbol": "charge",
            "change_type": "RETURN_TYPE_CHANGE",
        },
        "affected_components": [
            {
                "file": "invoice.py",
                "start_line": 50,
                "end_line": 55,
                "symbol": "generate_invoice",
                "relationship": "calls",
            }
        ],
        "call_chain": ["billing.py:charge", "invoice.py:generate_invoice"],
        "snippets": [
            {
                "file": "billing.py",
                "start_line": 15,
                "end_line": 20,
                "content": "return InvoiceRecord(...)",
            }
        ],
    }

    normalized = AnalyzerAdapter.normalize(raw_payload)
    assert normalized.project_id == "alternate-project-id"
    assert normalized.change.file == "billing.py"
    assert len(normalized.impacted_components) == 1
    assert normalized.impacted_components[0].file == "invoice.py"
    assert len(normalized.impact_chain) == 2
    assert len(normalized.evidence) == 1
    assert normalized.evidence[0].file == "billing.py"


def test_analyzer_adapter_rejects_invalid_type():
    """Test AnalyzerAdapter raises error on non-dict input."""
    with pytest.raises(ValueError):
        AnalyzerAdapter.normalize("invalid_string_input")  # type: ignore
