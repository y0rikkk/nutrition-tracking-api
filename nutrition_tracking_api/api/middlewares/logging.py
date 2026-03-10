"""Logging middleware for automatic HTTP request logging."""

import time
from typing import Any

import loguru
from fastapi import Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware для автоматического логирования всех HTTP запросов.

    Логирует:
    - Метод и путь запроса
    - Status code ответа
    - Длительность обработки запроса
    - X-Request-ID (если есть RequestIDMiddleware)
    - Дополнительные данные из request.state.log_payload
    - Исключения с полной трассировкой

    Использование:
        # Добавить ПОСЛЕ RequestIDMiddleware
        app.add_middleware(LoggingMiddleware)

    Пример лога:
        INFO: GET "/api/orders/" - 200
        extra: {"X-Request-ID": "...", "status_code": 200, "duration": 0.123}
    """

    def _get_extra(self, request: Request, status_code: int, duration: float) -> dict[str, Any]:
        """
        Собрать дополнительные данные для лога.

        Извлекает данные из request.state.log_payload (например, X-Request-ID)
        и добавляет status_code и duration.

        Args:
        ----
            request: FastAPI Request объект
            status_code: HTTP status code ответа
            duration: Длительность обработки запроса в секундах

        Returns:
        -------
            dict: Extra данные для логирования

        """
        extra: dict[str, Any] = {
            "status_code": status_code,
            "duration": duration,
        }

        # Добавить данные из request.state.log_payload (X-Request-ID, username, etc.)
        if log_payload := getattr(request.state, "log_payload", None):
            extra.update(**log_payload)

        return extra

    def _format_duration(self, duration: float) -> float:
        """
        Форматировать длительность до 3 знаков после запятой.

        Args:
        ----
            duration: Длительность в секундах

        Returns:
        -------
            float: Отформатированная длительность

        """
        return round(duration, 3)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """
        Обработка запроса с логированием.

        Args:
        ----
            request: Входящий запрос
            call_next: Следующий обработчик в цепочке

        Returns:
        -------
            Response: Ответ от приложения

        """
        # Подготовить базовое сообщение
        message = f'{request.method} "{request.url.path}"'

        # Засечь время начала
        start_time = time.time()

        try:
            # Обработать запрос
            response = await call_next(request)

            # Собрать extra данные для успешного запроса
            extra = self._get_extra(
                request,
                response.status_code,
                self._format_duration(time.time() - start_time),
            )

        except Exception:
            # Обработка исключений
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

            # Собрать extra данные для failed запроса
            extra = self._get_extra(
                request,
                status_code,
                self._format_duration(time.time() - start_time),
            )

            # Логировать с exception traceback
            loguru.logger.opt(exception=True).error(f"{message} - {status_code}", **extra)

            # Пробросить исключение дальше
            raise

        # Логировать успешный запрос
        message += f" - {response.status_code}"
        loguru.logger.info(message, **extra)

        return response
