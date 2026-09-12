"""Health check and configuration inspection endpoint."""

from fastapi import APIRouter
from app.config import settings
from app.models.responses import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def get_health() -> HealthResponse:
    """Return backend status, version, and active LLM configuration."""
    return HealthResponse(
        status="ok",
        version="1.0.0",
        demo_mode=settings.DEMO_MODE,
        llm_provider="demo" if settings.DEMO_MODE else settings.LLM_PROVIDER,
        model="mock-grounded" if settings.DEMO_MODE else settings.OPENAI_MODEL,
    )
