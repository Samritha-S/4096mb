"""OpenAI Provider implementation."""

import json
from typing import Any, Dict, Optional, Type
from openai import AsyncOpenAI, APITimeoutError, APIConnectionError, APIStatusError
from pydantic import BaseModel

from app.config import settings
from app.llm.base import LLMProvider
from app.utils.errors import LLMProviderException, MalformedLLMResponseException
from app.utils.logging import logger


class OpenAIProvider(LLMProvider):
    """OpenAI API integration for CodeImpact reasoning."""

    def __init__(self):
        if not settings.OPENAI_API_KEY:
            raise LLMProviderException("OPENAI_API_KEY is not configured.")

        self.client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            timeout=settings.OPENAI_TIMEOUT_SECONDS,
        )
        self.model = settings.OPENAI_MODEL

    async def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.0,
            )
            return response.choices[0].message.content or ""
        except APITimeoutError as e:
            logger.error(f"OpenAI API timeout: {e}")
            raise LLMProviderException(f"LLM request timed out after {settings.OPENAI_TIMEOUT_SECONDS}s.")
        except (APIConnectionError, APIStatusError) as e:
            logger.error(f"OpenAI API error: {e}")
            raise LLMProviderException(f"LLM provider error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error communicating with OpenAI: {e}")
            raise LLMProviderException(f"Unexpected LLM failure: {str(e)}")

    async def generate_structured(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        response_model: Optional[Type[BaseModel]] = None,
    ) -> Dict[str, Any]:
        """Generate structured JSON response adhering to json_object response format."""
        messages = []
        base_system = (
            "You are CodeImpact's deterministic reasoning assistant. "
            "You MUST respond ONLY with valid JSON conforming to the requested schema. "
            "Do not include markdown code block backticks around the JSON unless strictly necessary. "
            "Never invent files, functions, lines, or behaviors."
        )
        if system_prompt:
            base_system = f"{base_system}\n\n{system_prompt}"

        messages.append({"role": "system", "content": base_system})
        messages.append({"role": "user", "content": prompt})

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.0,
            )
            raw_content = response.choices[0].message.content or "{}"
            try:
                data = json.loads(raw_content)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM JSON response: {raw_content}")
                raise MalformedLLMResponseException(f"LLM returned invalid JSON: {str(e)}")

            if response_model:
                try:
                    # Validate against Pydantic schema
                    validated = response_model.model_validate(data)
                    return validated.model_dump()
                except Exception as val_err:
                    logger.warning(f"Schema validation error on LLM output: {val_err}")
                    # Return parsed data; reasoning engines will perform normalization
                    return data
            return data

        except (APITimeoutError, APIConnectionError, APIStatusError) as e:
            logger.error(f"OpenAI error in structured generation: {e}")
            raise LLMProviderException(f"LLM provider error: {str(e)}")
        except (LLMProviderException, MalformedLLMResponseException):
            raise
        except Exception as e:
            logger.error(f"Unexpected error in OpenAI structured call: {e}")
            raise LLMProviderException(f"Structured LLM generation failed: {str(e)}")
