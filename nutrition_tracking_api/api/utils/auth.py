"""Утилиты для аутентификации (JWT, токены)."""

import secrets
from datetime import datetime

import jwt
from jwt.algorithms import RSAAlgorithm

from nutrition_tracking_api.api.exceptions import AuthTokenExpiredError, AuthTokenValidateError
from nutrition_tracking_api.api.schemas.auth.common import SecretConfig
from nutrition_tracking_api.api.schemas.auth.user import UserCreate


def get_user_data_from_jwt_token(token: str, key: SecretConfig) -> UserCreate:
    """
    Декодировать TWork JWT токен и создать UserCreate схему.

    Args:
    ----
        token: JWT токен
        key: RSA публичный ключ из JWKS

    Returns:
    -------
        UserCreate схема с данными пользователя

    """
    public_key = RSAAlgorithm.from_jwk(key.model_dump())
    try:
        payload = jwt.decode(
            token,
            public_key,  # type: ignore[arg-type]
            algorithms=[key.alg],
            options={"verify_signature": True, "verify_aud": False, "exp": True},  # type: ignore[arg-type]
        )
    except jwt.exceptions.ExpiredSignatureError as e:
        raise AuthTokenExpiredError from e

    except jwt.exceptions.InvalidSignatureError as e:
        raise AuthTokenValidateError from e

    username = payload.get("uname") or payload.get("sub") or ""
    exp = payload.get("exp")
    ad_login = payload.get("ad", {}).get("login") if isinstance(payload.get("ad"), dict) else payload.get("ad_login")
    master_id = payload.get("master_id")
    full_name = payload.get("full_name") or payload.get("name")
    email = payload.get("email")

    expires_at = datetime.fromtimestamp(exp).astimezone() if exp else None

    return UserCreate(
        username=username,
        access_token=token,
        access_token_expires_at=expires_at,
        ad_login=ad_login,
        master_id=master_id,
        full_name=full_name,
        email=email,
    )


def get_jwt_token_header_mapping(token: str) -> dict[str, str]:
    """
    Извлечь заголовок JWT токена без верификации.

    Args:
    ----
        token: JWT токен

    Returns:
    -------
        Словарь с заголовком токена (alg, kid, etc.)

    """
    return jwt.get_unverified_header(token)


def create_token(username: str) -> str:
    """
    Создать уникальный service token для сервисных пользователей.

    Args:
    ----
        username: Имя пользователя

    Returns:
    -------
        Уникальный токен

    """
    return f"svc-{username}-{secrets.token_hex(16)}"
