"""Утилиты для аутентификации (JWT, пароли, токены)."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import bcrypt
import jwt

from nutrition_tracking_api.api.exceptions import AuthTokenExpiredError, AuthTokenValidateError
from nutrition_tracking_api.settings import settings


def hash_password(password: str) -> str:
    """
    Хешировать пароль через bcrypt.

    Args:
    ----
        password: Пароль в открытом виде

    Returns:
    -------
        Хеш пароля (UTF-8 строка)

    """
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Проверить пароль против хеша.

    Args:
    ----
        plain_password: Пароль в открытом виде
        hashed_password: Хеш из базы данных

    Returns:
    -------
        True если пароль совпадает

    """
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def create_access_token(user_id: str, username: str) -> str:
    """
    Создать JWT access токен (HS256, короткий срок жизни).

    Payload:
        sub: user_id (UUID строка)
        username: имя пользователя
        type: "access"
        exp: время истечения
        iat: время создания

    Args:
    ----
        user_id: UUID пользователя
        username: Имя пользователя

    Returns:
    -------
        Подписанный JWT токен

    """
    now = datetime.now(tz=timezone.utc)
    payload = {
        "sub": str(user_id),
        "username": username,
        "type": "access",
        "exp": now + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
        "iat": now,
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(user_id: str) -> tuple[str, str]:
    """
    Создать JWT refresh токен (HS256, длинный срок жизни).

    Refresh токен содержит уникальный jti (JWT ID), который сохраняется
    в БД для возможности отзыва (logout, rotation).

    Args:
    ----
        user_id: UUID пользователя

    Returns:
    -------
        Кортеж (токен, jti). jti нужно сохранить в БД.

    """
    now = datetime.now(tz=timezone.utc)
    jti = str(uuid4())
    payload = {
        "sub": str(user_id),
        "jti": jti,
        "type": "refresh",
        "exp": now + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
        "iat": now,
    }
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token, jti


def decode_token(token: str) -> dict:
    """
    Декодировать и верифицировать JWT токен (HS256).

    Args:
    ----
        token: JWT токен

    Returns:
    -------
        Payload словарь

    Raises:
    ------
        AuthTokenExpiredError: Если токен истёк
        AuthTokenValidateError: Если токен невалиден (неверная подпись, формат и т.д.)

    """
    try:
        return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except jwt.exceptions.ExpiredSignatureError as e:
        raise AuthTokenExpiredError from e
    except jwt.exceptions.InvalidTokenError as e:
        raise AuthTokenValidateError from e
