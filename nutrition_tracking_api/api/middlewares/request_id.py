"""Request ID middleware for distributed tracing."""

from uuid import uuid4

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware для добавления X-Request-ID к каждому запросу.

    Использует X-Request-ID из заголовка запроса или генерирует новый UUID.
    Сохраняет request_id в request.state для использования в логах и метриках.
    Возвращает X-Request-ID в заголовках ответа для трейсинга.

    Использование:
        app.add_middleware(RequestIDMiddleware)

    Доступ к request_id:
        request.state.request_id  # UUID строка
        request.state.log_payload  # {"X-Request-ID": "..."}
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """
        Обработка запроса с добавлением X-Request-ID.

        Args:
        ----
            request: Входящий запрос
            call_next: Следующий обработчик в цепочке

        Returns:
        -------
            Response: Ответ с X-Request-ID в headers

        """
        # Получить X-Request-ID из header или сгенерировать новый
        request_id = request.headers.get("X-Request-ID", str(uuid4()))

        # Сохранить в request.state для использования в приложении
        request.state.request_id = request_id

        # Сохранить в log_payload для автоматического добавления в логи
        request.state.log_payload = {"X-Request-ID": request_id}

        # Обработать запрос
        response = await call_next(request)

        # Добавить X-Request-ID в response headers для клиента
        response.headers["X-Request-ID"] = request_id

        return response
