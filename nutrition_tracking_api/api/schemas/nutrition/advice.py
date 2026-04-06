"""Pydantic схемы для эндпоинта советов по питанию."""

from pydantic import BaseModel, Field


class AdviceRequest(BaseModel):
    """Запрос на получение совета по питанию."""

    question: str | None = None
    days: int = Field(default=7, ge=1, le=30)


class AdviceOut(BaseModel):
    """Ответ с советом по питанию."""

    advice: str
