from fastapi import APIRouter

from backend.models.schemas import AskRequest, AskResponse
from backend.services.prompt_builder import build_prompt
from backend.services.search_client import SearchClient
from backend.services.llm_client import LLMClient

router = APIRouter()
search_client = SearchClient()
llm_client = LLMClient()

@router.post("/ask", response_model=AskResponse)
def ask_question(request: AskRequest) -> AskResponse:
    """Endpoint that accepts a user question and returns a grounded answer."""
    chunks = search_client.search(request.question, request.max_results)
    prompt = build_prompt(request.question, chunks)
    answer = llm_client.generate(prompt)

    return AskResponse(
        answer=answer,
        citations=[
            {
                "title": chunk.get("title", "Retrieved source"),
                "url": chunk.get("url", ""),
                "snippet": chunk.get("snippet", chunk.get("content", ""))
            }
            for chunk in chunks
        ],
    )
