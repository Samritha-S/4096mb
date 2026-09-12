"""Factory for instantiating LLM providers."""

from app.config import settings
from app.llm.base import LLMProvider
from app.llm.demo_provider import DemoProvider
from app.llm.openai_provider import OpenAIProvider
from app.utils.logging import logger


def get_llm_provider() -> LLMProvider:
    """Return an active LLMProvider instance based on system configuration."""
    if settings.DEMO_MODE or not settings.OPENAI_API_KEY:
        if not settings.DEMO_MODE:
            logger.warning("DEMO_MODE is false but OPENAI_API_KEY is unset. Falling back to DemoProvider.")
        return DemoProvider()

    provider_name = settings.LLM_PROVIDER.lower()
    if provider_name == "openai":
        return OpenAIProvider()
    else:
        logger.warning(f"Unknown LLM provider '{provider_name}'. Defaulting to DemoProvider.")
        return DemoProvider()
