"""Pytest fixtures and test environment setup."""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings
from app.models.common import EvidenceSnippet
from app.models.requests import ChangeDetail, ImpactAnalysisInput, ImpactedComponent

# Ensure tests run in DEMO_MODE without external network dependencies
settings.DEMO_MODE = True


@pytest.fixture
def client():
    """Synchronous test client for FastAPI application."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def sample_impact_input():
    """Standard sample input from Person 2 analyzer."""
    return ImpactAnalysisInput(
        project_id="demo-project",
        change=ChangeDetail(
            file="cart.py",
            start_line=42,
            end_line=48,
            symbol="calculate_total",
            change_type="RETURN_TYPE_CHANGE",
            description="Return type changed from dictionary to CartTotal",
            before="return {'subtotal': subtotal, 'tax': tax}",
            after="return CartTotal(subtotal, tax)",
        ),
        impacted_components=[
            ImpactedComponent(
                file="payment.py",
                start_line=87,
                end_line=90,
                symbol="process_payment",
                relationship="calls",
                details="Invokes calculate_total",
            )
        ],
        impact_chain=[
            "cart.py:calculate_total",
            "payment.py:process_payment",
            "checkout.py:checkout",
        ],
        evidence=[
            EvidenceSnippet(
                file="cart.py",
                start_line=42,
                end_line=48,
                content="def calculate_total(cart):\n    subtotal = sum(item['price'] for item in cart)\n    tax = round(subtotal * 0.08, 2)\n    return CartTotal(subtotal, tax)\n",
                symbol="calculate_total",
            ),
            EvidenceSnippet(
                file="payment.py",
                start_line=87,
                end_line=90,
                content="    total = calculate_total(cart)\n    tax = total['tax']\n    subtotal = total['subtotal']\n",
                symbol="process_payment",
            ),
        ],
    )
