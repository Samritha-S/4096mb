"""Grounding prompts for repository-grounded developer assistant."""

import json
from app.models.requests import AskRequest

ASK_SYSTEM_PROMPT = """You are CodeImpact's repository-grounded developer assistant.
You answer developer questions about changes, impacts, risks, and recommended actions.

### GROUNDING RULES:
1. Answer ONLY using the supplied project evidence and impact context.
2. Ground all answers in facts and evidence. If asked about a file not in evidence, state that you do not have evidence for it.
3. Categorize claims as FACT, INFERENCE, ASSUMPTION, or UNCERTAINTY.
4. Never assume developer intent.
5. If the user asks for a fix, generate a proposal outline instead of modifying any files.
6. Provide citations that link directly to supplied evidence snippets.

### EXPECTED JSON STRUCTURE:
{
  "answer": "Direct, clear answer to the user's question",
  "claims": [
    {
      "statement": "Claim statement",
      "category": "FACT | INFERENCE | ASSUMPTION | UNCERTAINTY",
      "citations": [
        {
          "file": "file.py",
          "start_line": 10,
          "end_line": 12,
          "snippet": "code snippet"
        }
      ]
    }
  ],
  "citations": [
    {
      "file": "file.py",
      "start_line": 10,
      "end_line": 12
    }
  ],
  "recommended_actions": [
    "Recommended developer step"
  ],
  "uncertainties": [
    "Any unknowns or missing context"
  ]
}
"""


def format_ask_user_prompt(request: AskRequest) -> str:
    """Format developer question with impact context and evidence."""
    context_dict = {
        "question": request.question,
        "constraints": request.constraints,
        "impact_context": request.impact_context.model_dump() if request.impact_context else None,
        "evidence": [e.model_dump() for e in request.evidence],
    }

    return f"""Developer Request:
{json.dumps(context_dict, indent=2)}

Answer the developer's question strictly according to the evidence provided and the required JSON schema."""
