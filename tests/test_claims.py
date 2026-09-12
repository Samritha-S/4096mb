"""Tests for deterministic Claim and Citation Verifier."""

from app.models.common import Claim, ClaimCategory, CodeCitation, EvidenceSnippet
from app.reasoning.claim_verifier import ClaimVerifier


def test_verify_valid_citation():
    """Test citation with matching file, range, and snippet verifies successfully."""
    evidence = [
        EvidenceSnippet(
            file="payment.py",
            start_line=85,
            end_line=95,
            content="    total = calculate_total(cart)\n    tax = total['tax']\n",
        )
    ]
    citation = CodeCitation(
        file="payment.py",
        start_line=87,
        end_line=89,
        snippet="tax = total['tax']",
    )

    verified = ClaimVerifier.verify_citation(citation, evidence)
    assert verified.verified is True
    assert "Verified" in verified.verification_notes


def test_verify_hallucinated_file():
    """Test citation with hallucinated file is flagged as unverified."""
    evidence = [
        EvidenceSnippet(
            file="cart.py",
            start_line=1,
            end_line=10,
            content="def calculate_total(): pass",
        )
    ]
    citation = CodeCitation(
        file="database.py",
        start_line=500,
        end_line=505,
    )

    verified = ClaimVerifier.verify_citation(citation, evidence)
    assert verified.verified is False
    assert "not present in supplied evidence" in verified.verification_notes


def test_verify_hallucinated_line_number():
    """Test citation referencing lines outside evidence range is flagged."""
    evidence = [
        EvidenceSnippet(
            file="payment.py",
            start_line=80,
            end_line=90,
            content="total = calculate_total(cart)",
        )
    ]
    citation = CodeCitation(
        file="payment.py",
        start_line=500,
        end_line=505,
    )

    verified = ClaimVerifier.verify_citation(citation, evidence)
    assert verified.verified is False
    assert "outside evidence line ranges" in verified.verification_notes


def test_verify_claims_list():
    """Test batch claim verification."""
    evidence = [
        EvidenceSnippet(
            file="cart.py",
            start_line=40,
            end_line=50,
            content="return CartTotal(subtotal, tax)",
        )
    ]
    claims = [
        Claim(
            statement="cart.py returns CartTotal",
            category=ClaimCategory.FACT,
            citations=[
                CodeCitation(file="cart.py", start_line=42, end_line=48)
            ],
        ),
        Claim(
            statement="Database schema broke",
            category=ClaimCategory.INFERENCE,
            citations=[
                CodeCitation(file="db.py", start_line=1, end_line=5)
            ],
        ),
    ]

    verified_claims = ClaimVerifier.verify_claims(claims, evidence)
    assert verified_claims[0].verified is True
    assert verified_claims[1].verified is False
