"""Repository-grounded developer assistant endpoint.

INTEGRATION (HB-26): This endpoint now automatically retrieves relevant
code chunks from Person 1's chunks.json via the retrieval_bridge (Person 2's
CodebaseRetriever).  The caller only needs to send { "question": "..." } —
the evidence is fetched semantically, not passed in the request body.

Backwards-compatible: if the caller still sends evidence snippets or
impact_context in the request they are merged with the retrieved evidence,
giving Person 4 full flexibility.
"""

from typing import List

from fastapi import APIRouter, Depends

from app.llm.base import LLMProvider
from app.llm.factory import get_llm_provider
from app.models.common import Claim, CodeCitation, ConfidenceLevel
from app.models.requests import AskRequest, FixProposalRequest
from app.models.responses import AskResponse
from app.prompts.ask_prompt import ASK_SYSTEM_PROMPT, format_ask_user_prompt
from app.reasoning.claim_verifier import ClaimVerifier
from app.reasoning.fix_engine import FixEngine
from app.reasoning.intent import IntentAnalyzer
from app.retrieval_bridge import search_codebase, is_ready
from app.utils.logging import logger

router = APIRouter()


@router.post("/ask", response_model=AskResponse)
async def ask_assistant(
    payload: AskRequest,
    llm: LLMProvider = Depends(get_llm_provider),
) -> AskResponse:
    """Answer developer questions grounded in repository evidence.

    Integration flow (Person 1 → 2 → 3):
      1. Embed the question (Person 2 / retrieval_bridge).
      2. Retrieve top-5 semantically relevant chunks from chunks.json (Person 1 output).
      3. Convert chunks → EvidenceSnippets and merge with any caller-supplied evidence.
      4. Build prompt and call LLM (Person 3).
      5. Verify citations against retrieved evidence and return response.
    """
    logger.info("Received developer inquiry: '%s'", payload.question)

    # ── Step 1: Retrieve evidence from codebase (P1 → P2 → here) ─────────────
    if is_ready():
        retrieved_evidence = search_codebase(payload.question, top_k=5)
        logger.info(
            "Retrieved %d evidence chunks from codebase for question: '%s...'",
            len(retrieved_evidence),
            payload.question[:60],
        )
    else:
        retrieved_evidence = []
        logger.warning(
            "Retrieval bridge not ready — no chunks loaded. "
            "Running on caller-supplied evidence only (or demo mock if none)."
        )

    # ── Step 2: Merge evidence sources ────────────────────────────────────────
    # Priority: retrieved (semantic) > caller-supplied > impact context
    all_evidence = list(retrieved_evidence)

    # Append any additional evidence the caller sent (may include local diffs etc.)
    for ev in payload.evidence:
        if not any(e.file == ev.file and e.start_line == ev.start_line for e in all_evidence):
            all_evidence.append(ev)

    if payload.impact_context and payload.impact_context.evidence:
        for ev in payload.impact_context.evidence:
            if not any(e.file == ev.file and e.start_line == ev.start_line for e in all_evidence):
                all_evidence.append(ev)

    logger.debug("Total evidence snippets for prompt: %d", len(all_evidence))

    # ── Step 3: Build a patched request carrying retrieved evidence ────────────
    # We patch the request so format_ask_user_prompt sees the full evidence set.
    patched_payload = AskRequest(
        question=payload.question,
        project_id=payload.project_id,
        impact_context=payload.impact_context,
        evidence=all_evidence,          # ← now includes retrieved chunks
        constraints=payload.constraints,
    )

    # ── Step 4: Query LLM ─────────────────────────────────────────────────────
    prompt = format_ask_user_prompt(patched_payload)
    raw_response = await llm.generate_structured(
        prompt=prompt,
        system_prompt=ASK_SYSTEM_PROMPT,
    )

    # ── Step 5: Extract and verify claims ─────────────────────────────────────
    raw_claims = raw_response.get("claims", [])
    claims: List[Claim] = []
    for c in raw_claims:
        if isinstance(c, dict):
            citations = [
                CodeCitation(**cit) if isinstance(cit, dict) else cit
                for cit in c.get("citations", [])
            ]
            claims.append(
                Claim(
                    statement=c.get("statement", ""),
                    category=c.get("category", "INFERENCE"),
                    citations=citations,
                )
            )

    ClaimVerifier.verify_claims(claims, all_evidence)

    # Citations at top level
    raw_citations = raw_response.get("citations", [])
    citations: List[CodeCitation] = []
    for cit in raw_citations:
        citation_obj = CodeCitation(**cit) if isinstance(cit, dict) else cit
        ClaimVerifier.verify_citation(citation_obj, all_evidence)
        citations.append(citation_obj)

    # ── Step 6: Optional fix proposal ─────────────────────────────────────────
    fix_proposal = None
    if IntentAnalyzer.is_fix_request(payload.question) and payload.impact_context:
        fix_req = FixProposalRequest(
            instruction=payload.question,
            constraints=payload.constraints,
            impact_analysis=payload.impact_context,
            evidence=all_evidence,
        )
        from app.prompts.fix_prompt import FIX_SYSTEM_PROMPT, format_fix_user_prompt
        fix_prompt = format_fix_user_prompt(fix_req)
        raw_fix = await llm.generate_structured(
            prompt=fix_prompt, system_prompt=FIX_SYSTEM_PROMPT
        )
        fix_proposal = FixEngine.evaluate_and_build_proposal(fix_req, raw_fix)

    # ── Step 7: Confidence score ───────────────────────────────────────────────
    total_cit = len(citations) + sum(len(c.citations) for c in claims)
    ver_cit = (
        sum(1 for c in citations if c.verified)
        + sum(1 for c in claims for cit in c.citations if cit.verified)
    )

    if total_cit > 0 and (ver_cit / total_cit) >= 0.8:
        confidence = ConfidenceLevel.HIGH
    elif not all_evidence:
        confidence = ConfidenceLevel.LOW
    else:
        confidence = ConfidenceLevel.MEDIUM

    return AskResponse(
        answer=raw_response.get(
            "answer",
            "No answer could be determined from the supplied evidence.",
        ),
        claims=claims,
        citations=citations,
        recommended_actions=raw_response.get("recommended_actions", []),
        confidence=confidence,
        uncertainties=raw_response.get("uncertainties", []),
        fix_proposal=fix_proposal,
    )
