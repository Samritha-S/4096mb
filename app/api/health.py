"""Health check and configuration inspection endpoint — with retrieval status."""

from fastapi import APIRouter
from pydantic import BaseModel

from app.config import settings
from app.models.responses import HealthResponse
from app.retrieval_bridge import get_status as retrieval_status

router = APIRouter()


class FullHealthResponse(BaseModel):
    """Extended health response including retrieval bridge status."""
    status: str = "ok"
    version: str = "1.0.0"
    demo_mode: bool
    llm_provider: str
    model: str
    retrieval_ready: bool
    chunks_count: int
    chunks_file: str
    embedding_model: str
    embedding_backend: str


@router.get("/health", response_model=FullHealthResponse)
async def get_health() -> FullHealthResponse:
    """Return backend status, LLM config, and retrieval bridge status."""
    rs = retrieval_status()
    return FullHealthResponse(
        status="ok",
        version="1.0.0",
        demo_mode=settings.DEMO_MODE,
        llm_provider="demo" if settings.DEMO_MODE else settings.LLM_PROVIDER,
        model="mock-grounded" if settings.DEMO_MODE else settings.OPENAI_MODEL,
        retrieval_ready=rs["retrieval_ready"],
        chunks_count=rs["chunks_count"],
        chunks_file=rs["chunks_file"],
        embedding_model=rs["embedding_model"],
        embedding_backend=rs["embedding_backend"],
    )
