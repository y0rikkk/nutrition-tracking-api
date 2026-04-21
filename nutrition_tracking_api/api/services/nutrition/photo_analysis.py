"""Сервис для распознавания блюд на фото через vision LLM."""

import base64
import json
from typing import Any

from fastapi import UploadFile
from loguru import logger
from pydantic import ValidationError

from nutrition_tracking_api.api.exceptions import (
    PhotoAnalysisInvalidResponseError,
    PhotoAnalysisNoDishesError,
    UnsupportedImageFormatError,
)
from nutrition_tracking_api.api.schemas.nutrition.photo_analysis import PhotoAnalysisOut
from nutrition_tracking_api.integrations.openrouter import OpenRouterClient

_ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}

_SYSTEM_PROMPT = "Ты ассистент-диетолог. Анализируй фото еды и возвращай ТОЛЬКО валидный JSON без markdown-обёрток. Названия пиши на РУССКОМ ЯЗЫКЕ."

_USER_PROMPT = (
    "Определи все блюда и продукты питания на фото. Верни JSON строго в формате:\n"
    '{"dishes": [{"name": "...", "amount_g": 200, "calories_kcal": 300, "protein_g": 15, "fat_g": 10, "carbs_g": 35}]}\n'  # noqa: E501
    'Оценивай порции визуально. Если блюдо не распознано — верни {"dishes": []}.'
)


class PhotoAnalysisService:
    """Отправляет фото в vision LLM и возвращает список распознанных блюд с КБЖУ."""

    def analyze(self, photo: UploadFile) -> PhotoAnalysisOut:
        """Распознать блюда на фото."""
        if photo.content_type not in _ALLOWED_CONTENT_TYPES:
            raise UnsupportedImageFormatError
        photo_bytes = photo.file.read()
        b64 = base64.b64encode(photo_bytes).decode()
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": _USER_PROMPT},
                    {"type": "image_url", "image_url": {"url": f"data:{photo.content_type};base64,{b64}"}},
                ],
            },
        ]

        raw = OpenRouterClient().chat(messages)
        return self._parse_response(raw)

    def _parse_response(self, raw: str) -> PhotoAnalysisOut:
        """Распарсить JSON-ответ LLM в PhotoAnalysisOut."""
        cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning("PhotoAnalysis: LLM returned non-JSON: {}", raw[:200])
            raise PhotoAnalysisInvalidResponseError from None

        try:
            result = PhotoAnalysisOut(**data)
        except (ValidationError, TypeError):
            logger.warning("PhotoAnalysis: LLM JSON failed validation: {}", data)
            raise PhotoAnalysisInvalidResponseError from None

        if not result.dishes:
            raise PhotoAnalysisNoDishesError

        return result
