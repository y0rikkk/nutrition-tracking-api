"""Utility functions for metrics."""

from fastapi import Request

from nutrition_tracking_api.api.dependencies.auth import (
    auth_token_obtain,
    service_token_obtain,
)
from nutrition_tracking_api.api.services.auth.authorization import AuthService
from nutrition_tracking_api.api.utils.auth import (
    get_jwt_token_header_mapping,
    get_user_data_from_jwt_token,
)
from nutrition_tracking_api.integrations.twork import get_secret_config


def get_username_from_request(request: Request) -> str:
    """
    Извлекает username из запроса.

    Пытается извлечь username из JWT токена в Authorization header.
    Если токен отсутствует или невалиден, возвращает "undefined".

    Args:
    ----
        request: FastAPI Request объект

    Returns:
    -------
        str: Username из токена или "undefined"


    """
    auth_token = auth_token_obtain(request)
    service_token = service_token_obtain(request)
    if not auth_token and not service_token:
        return "undefined"
    token = auth_token or service_token
    try:
        token_header = get_jwt_token_header_mapping(token)  # type: ignore[arg-type]
        secret_config = get_secret_config()
        secret_key = AuthService.get_secret_key_by_jwt_token_header(token_header, secret_config)
        user_data = get_user_data_from_jwt_token(auth_token or service_token, key=secret_key)  # type: ignore[arg-type]
    except Exception:  # noqa: BLE001
        return "undefined"

    return user_data.username
