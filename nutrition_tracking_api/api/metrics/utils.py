"""Utility functions for metrics."""

from fastapi import Request


def get_username_from_request(request: Request) -> str:
    """
    Извлекает username из запроса для метрик Prometheus.

    Использует request.state.log_payload, который устанавливается в
    AuthService._set_request_state для всех аутентифицированных запросов
    (и Bearer JWT, и Service Token).

    Возвращает "undefined" для неаутентифицированных и публичных запросов.
    """
    log_payload = getattr(request.state, "log_payload", None)
    if log_payload:
        return str(log_payload.get("username", "undefined"))
    return "undefined"
