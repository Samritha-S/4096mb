"""Main FastAPI Application Entrypoint — HB-26 Integrated Backend.

Integration changes vs original Person 3 code:
  - lifespan: calls retrieval_bridge.init_retriever() at startup so P1's
    chunks.json is loaded once and reused across all /ask requests.
  - /health: includes retrieval_bridge status so the team can confirm the
    P1→P2 pipeline is live before demoing.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router
from app.config import settings
from app.retrieval_bridge import init_retriever, get_status as retrieval_status
from app.utils.errors import register_error_handlers
from app.utils.logging import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle: load retrieval index at startup."""
    logger.info(
        "Starting HB-26 Integrated Backend v1.0.0 "
        "(DEMO_MODE=%s, LLM_PROVIDER=%s)",
        settings.DEMO_MODE,
        settings.LLM_PROVIDER,
    )

    # ── Load Person 1's chunks.json into Person 2's retriever ─────────────────
    loaded = init_retriever()
    if loaded:
        status = retrieval_status()
        logger.info(
            "Retrieval ready: %d chunks from '%s' using model '%s'",
            status["chunks_count"],
            status["chunks_file"],
            status["embedding_model"],
        )
    else:
        logger.warning(
            "No chunks.json loaded — /ask will use demo mock responses. "
            "Set CHUNKS_FILE in .env or run: python ingestion/main.py --repo <path>"
        )

    yield

    logger.info("Shutting down HB-26 Integrated Backend.")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance."""
    app = FastAPI(
        title="HB-26 Codebase Intelligence Backend",
        description=(
            "Integrated backend: Person 1 ingestion → Person 2 retrieval → "
            "Person 3 LLM answer layer. Accepts plain-English questions about "
            "any codebase and returns grounded answers with file/line citations."
        ),
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.get_cors_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_error_handlers(app)
    app.include_router(api_router)

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
