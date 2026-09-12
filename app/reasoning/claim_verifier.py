"""Deterministic Citation and Claim Verifier."""

from typing import List, Optional, Tuple
from app.models.common import (
    Claim,
    CodeCitation,
    EvidenceSnippet,
)
from app.models.responses import CitationVerificationResult
from app.utils.logging import logger


class ClaimVerifier:
    """Performs deterministic verification of citations and claims against supplied repository evidence."""

    @staticmethod
    def _normalize_filename(path: str) -> str:
        """Normalize file path for consistent matching."""
        if not path:
            return ""
        norm = path.replace("\\", "/").strip().lower()
        if norm.startswith("./"):
            norm = norm[2:]
        return norm

    @classmethod
    def _match_evidence_file(cls, citation_file: str, evidence: List[EvidenceSnippet]) -> List[EvidenceSnippet]:
        """Find evidence snippets matching the cited file name or path."""
        c_norm = cls._normalize_filename(citation_file)
        c_base = c_norm.split("/")[-1]

        matches = []
        for e in evidence:
            e_norm = cls._normalize_filename(e.file)
            e_base = e_norm.split("/")[-1]
            if c_norm == e_norm or c_base == e_base:
                matches.append(e)
        return matches

    @classmethod
    def verify_citation(cls, citation: CodeCitation, evidence: List[EvidenceSnippet]) -> CodeCitation:
        """Deterministically verify a single citation against supplied evidence snippets."""
        matching_snippets = cls._match_evidence_file(citation.file, evidence)

        if not matching_snippets:
            citation.verified = False
            citation.verification_notes = f"File '{citation.file}' not present in supplied evidence."
            return citation

        # If line numbers are specified, check if covered by snippet line ranges
        if citation.start_line is not None:
            c_start = citation.start_line
            c_end = citation.end_line if citation.end_line is not None else citation.start_line

            range_matched = False
            for snippet in matching_snippets:
                if snippet.start_line <= c_start and c_end <= snippet.end_line:
                    range_matched = True
                    # If snippet text is specified, check content presence
                    if citation.snippet:
                        clean_cited_snippet = citation.snippet.strip()
                        if clean_cited_snippet in snippet.content:
                            citation.verified = True
                            citation.verification_notes = (
                                f"Verified: lines {c_start}-{c_end} and content match evidence in {snippet.file}"
                            )
                            return citation
                        else:
                            # Try line-by-line whitespace-insensitive match
                            snippet_lines = [line.strip() for line in snippet.content.splitlines()]
                            if any(clean_cited_snippet in s_line or s_line in clean_cited_snippet for s_line in snippet_lines):
                                citation.verified = True
                                citation.verification_notes = (
                                    f"Verified: lines {c_start}-{c_end} matched with trimmed snippet in {snippet.file}"
                                )
                                return citation
                    else:
                        citation.verified = True
                        citation.verification_notes = (
                            f"Verified: line range {c_start}-{c_end} within evidence range {snippet.start_line}-{snippet.end_line} of {snippet.file}"
                        )
                        return citation

            if not range_matched:
                available_ranges = ", ".join(f"{s.start_line}-{s.end_line}" for s in matching_snippets)
                citation.verified = False
                citation.verification_notes = (
                    f"Line range {c_start}-{c_end} outside evidence line ranges ({available_ranges}) in '{citation.file}'."
                )
                return citation
        else:
            # No line numbers provided, check if cited snippet exists in file content
            if citation.snippet:
                clean_cited_snippet = citation.snippet.strip()
                for snippet in matching_snippets:
                    if clean_cited_snippet in snippet.content:
                        citation.verified = True
                        citation.verification_notes = f"Verified: content found in {snippet.file}"
                        return citation
                citation.verified = False
                citation.verification_notes = f"Cited snippet not found in supplied content of '{citation.file}'."
                return citation
            else:
                # File exists in evidence
                citation.verified = True
                citation.verification_notes = f"Verified: file '{citation.file}' exists in evidence."
                return citation

        citation.verified = False
        citation.verification_notes = "Citation could not be verified against evidence."
        return citation

    @classmethod
    def verify_claims(cls, claims: List[Claim], evidence: List[EvidenceSnippet]) -> List[Claim]:
        """Deterministically verify all citations in a list of claims."""
        for claim in claims:
            all_verified = True if claim.citations else False
            for citation in claim.citations:
                cls.verify_citation(citation, evidence)
                if not citation.verified:
                    all_verified = False
            claim.verified = all_verified
        return claims

    @classmethod
    def verify_all_citations(
        cls, citations: List[CodeCitation], evidence: List[EvidenceSnippet]
    ) -> CitationVerificationResult:
        """Verify an arbitrary list of citations and return a summary report."""
        verified_list = []
        failed_list = []

        for citation in citations:
            checked = cls.verify_citation(citation.model_copy(), evidence)
            if checked.verified:
                verified_list.append(checked)
            else:
                failed_list.append(checked)

        total = len(citations)
        v_count = len(verified_list)
        f_count = len(failed_list)

        if total == 0:
            summary = "No citations provided for verification."
        elif f_count == 0:
            summary = f"All {total} citations successfully verified against supplied evidence."
        else:
            summary = f"{v_count}/{total} citations verified. {f_count} failed verification."

        return CitationVerificationResult(
            total_citations=total,
            verified_count=v_count,
            unverified_count=f_count,
            verified_citations=verified_list,
            failed_citations=failed_list,
            summary=summary,
        )
