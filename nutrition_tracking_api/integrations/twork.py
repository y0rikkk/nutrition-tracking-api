"""TWork интеграция — получение JWKS для верификации JWT."""

from functools import lru_cache

import httpx

from nutrition_tracking_api.api.schemas.auth.common import SecretConfig
from nutrition_tracking_api.settings import settings


class TWORKClient:
    """HTTP клиент для получения JWKS из TWork."""

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def get_jwks(self) -> list[SecretConfig]:
        """
        Получить список публичных ключей из JWKS endpoint.

        Returns
        -------
            Список SecretConfig с публичными ключами

        """
        jwks_url = f"{self.base_url}/.well-known/openid-configuration/jwks"
        response = httpx.get(jwks_url, timeout=10.0)
        response.raise_for_status()
        data = response.json()
        keys = data.get("keys", [])
        return [SecretConfig(**key) for key in keys]


@lru_cache
def get_secret_config() -> list[SecretConfig]:
    """
    Получить публичные ключи из TWork JWKS (с кешированием).

    Returns
    -------
        Список SecretConfig

    """
    client = TWORKClient(settings.twork_api_endpoint)
    return client.get_jwks()
