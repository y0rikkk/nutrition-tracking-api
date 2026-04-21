"""OpenRouter API client."""

from typing import Any

import httpx
from loguru import logger

from nutrition_tracking_api.api.exceptions import LLMServiceError
from nutrition_tracking_api.settings import settings


class OpenRouterClient:
    """Синхронный HTTP клиент для OpenRouter API."""

    def __init__(self) -> None:
        self.api_key = settings.OPENROUTER_API_KEY
        self.model = settings.OPENROUTER_MODEL
        self.base_url = settings.OPENROUTER_BASE_URL

    def chat(self, messages: list[dict[str, Any]]) -> str:
        """Отправить список сообщений в LLM и получить текстовый ответ."""
        try:
            response = httpx.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={"model": self.model, "messages": messages, "reasoning": {"enabled": False}},
                timeout=60.0,
            )
            response.raise_for_status()
            return str(response.json()["choices"][0]["message"]["content"])
        except httpx.HTTPStatusError as e:
            logger.error("OpenRouter HTTP error: {} {}", e.response.status_code, e.response.text)
            raise LLMServiceError from e
        except Exception as e:
            logger.error("OpenRouter unexpected error: {}", e)
            raise LLMServiceError from e
