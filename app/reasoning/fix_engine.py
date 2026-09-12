"""Safe, No-Assumption Code Rewrite Proposal Engine with Unified Diff Generation."""

import difflib
from typing import Any, Dict, List, Optional
from app.models.common import (
    CodeCitation,
    ConfidenceLevel,
    EvidenceSnippet,
    FixStatus,
)
from app.models.requests import FixProposalRequest
from app.models.responses import FixChange, FixProposalResponse
from app.reasoning.claim_verifier import ClaimVerifier
from app.utils.logging import logger


class FixEngine:
    """Generates strictly verified fix proposals with unified diffs, refusing to guess developer intent or unevidenced APIs."""

    @staticmethod
    def generate_unified_diff(file_path: str, old_code: str, new_code: str, start_line: int) -> str:
        """Generate a standard unified diff string from old and new code snippets."""
        old_lines = old_code.splitlines(keepends=True)
        new_lines = new_code.splitlines(keepends=True)

        # Ensure newline endings
        old_lines = [line if line.endswith("\n") else line + "\n" for line in old_lines]
        new_lines = [line if line.endswith("\n") else line + "\n" for line in new_lines]

        diff = difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=f"a/{file_path}",
            tofile=f"b/{file_path}",
            fromfiledate="",
            tofiledate="",
            lineterm="\n",
        )
        return "".join(diff)

    @classmethod
    def evaluate_and_build_proposal(
        cls,
        request: FixProposalRequest,
        raw_fix_data: Dict[str, Any],
    ) -> FixProposalResponse:
        """Enforce strict evidence grounding and build verified FixProposalResponse."""
        instruction = request.instruction.strip().lower()

        # 1. Check for ambiguous or contradictory developer intent
        if len(instruction) < 5 or instruction in ("fix", "fix it", "make it work", "do something"):
            return FixProposalResponse(
                status=FixStatus.NEEDS_CLARIFICATION,
                summary="Developer instruction is ambiguous. Please provide explicit intent for the fix.",
                changes=[],
                diff=None,
                assumptions=[],
                uncertainties=["Ambiguous developer intent provided."],
                confidence=ConfidenceLevel.LOW,
                message="Please clarify the desired fix strategy, target callers, or boundary constraints.",
            )

        status_str = raw_fix_data.get("status", "PROPOSED").upper()

        if status_str in ("NEEDS_MORE_EVIDENCE", "NEEDS_CLARIFICATION"):
            return FixProposalResponse(
                status=FixStatus(status_str),
                summary=raw_fix_data.get("summary", "Additional evidence required to propose safe fix."),
                changes=[],
                diff=None,
                assumptions=raw_fix_data.get("assumptions", []),
                uncertainties=raw_fix_data.get("uncertainties", ["Missing evidence for caller or type definitions."]),
                confidence=ConfidenceLevel.MEDIUM,
                message=raw_fix_data.get("message", "Please supply evidence demonstrating the required contracts."),
            )

        raw_changes = raw_fix_data.get("changes", [])
        if not raw_changes:
            return FixProposalResponse(
                status=FixStatus.NEEDS_MORE_EVIDENCE,
                summary="No safe code rewrite could be established from supplied evidence.",
                changes=[],
                diff=None,
                assumptions=[],
                uncertainties=["Supplied evidence does not support automated rewrite."],
                confidence=ConfidenceLevel.LOW,
                message="Cannot propose code changes without matching evidence in caller files.",
            )

        # 2. Check each change against evidence
        verified_changes: List[FixChange] = []
        diff_chunks: List[str] = []
        all_evidence = request.evidence + request.impact_analysis.evidence
        has_failed_citations = False

        for ch in raw_changes:
            file_name = ch.get("file", "")
            start_l = ch.get("start_line", 1)
            end_l = ch.get("end_line", start_l)
            old_code = ch.get("old_code", "")
            new_code = ch.get("new_code", "")
            reason = ch.get("reason", "Adapted to updated contract.")

            # Validate that old_code exists in evidence
            matching_snippets = [
                e for e in all_evidence if file_name.endswith(e.file) or e.file.endswith(file_name)
            ]

            if not matching_snippets:
                return FixProposalResponse(
                    status=FixStatus.NEEDS_MORE_EVIDENCE,
                    summary=f"Proposed change targets file '{file_name}' which is missing from supplied evidence.",
                    changes=[],
                    diff=None,
                    assumptions=[],
                    uncertainties=[f"File '{file_name}' not provided in repository evidence."],
                    confidence=ConfidenceLevel.LOW,
                    message=f"Please provide evidence snippet covering '{file_name}' lines {start_l}-{end_l}.",
                )

            # Check line match and old_code substring
            snippet_has_old_code = False
            for snippet in matching_snippets:
                if old_code.strip() in snippet.content:
                    snippet_has_old_code = True
                    break

            if not snippet_has_old_code:
                return FixProposalResponse(
                    status=FixStatus.NEEDS_MORE_EVIDENCE,
                    summary=f"Old code '{old_code.strip()}' does not match supplied evidence content in '{file_name}'.",
                    changes=[],
                    diff=None,
                    assumptions=[],
                    uncertainties=[f"Old code mismatch in '{file_name}' lines {start_l}-{end_l}"],
                    confidence=ConfidenceLevel.LOW,
                    message="Refusing to propose rewrite because existing code line could not be verified.",
                )

            # Verify citations
            raw_citations = ch.get("citations", [])
            verified_citations: List[CodeCitation] = []
            for c_dict in raw_citations:
                citation = CodeCitation(**c_dict) if isinstance(c_dict, dict) else c_dict
                ClaimVerifier.verify_citation(citation, all_evidence)
                verified_citations.append(citation)
                if not citation.verified:
                    has_failed_citations = True

            change_obj = FixChange(
                file=file_name,
                start_line=start_l,
                end_line=end_l,
                old_code=old_code,
                new_code=new_code,
                reason=reason,
                citations=verified_citations,
            )
            verified_changes.append(change_obj)

            # Generate unified diff
            diff_str = cls.generate_unified_diff(file_name, old_code, new_code, start_l)
            diff_chunks.append(diff_str)

        full_diff = "\n".join(diff_chunks)
        confidence = ConfidenceLevel.HIGH if not has_failed_citations else ConfidenceLevel.MEDIUM

        return FixProposalResponse(
            status=FixStatus.PROPOSED,
            summary=raw_fix_data.get("summary", f"Proposed fix for {len(verified_changes)} component(s)."),
            changes=verified_changes,
            diff=full_diff,
            assumptions=raw_fix_data.get("assumptions", []),
            uncertainties=raw_fix_data.get("uncertainties", []),
            confidence=confidence,
            message="Fix proposal generated safely from evidence. Review diff before approval.",
        )
