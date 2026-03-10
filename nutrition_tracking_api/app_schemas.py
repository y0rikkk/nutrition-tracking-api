"""Common Pydantic schemas for the application."""

from dataclasses import dataclass

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    message: str | None = None


@dataclass
class RequestState:
    """
    Состояние запроса для передачи в сервисы.

    Attributes
    ----------
        request_id: Уникальный идентификатор запроса (X-Request-ID)

    """

    request_id: str | None = None
