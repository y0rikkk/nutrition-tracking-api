"""Схемы для аутентификации (login, register, token response)."""

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Запрос на вход по логину и паролю."""

    username: str
    password: str


class RegisterRequest(BaseModel):
    """Запрос на регистрацию нового пользователя."""

    username: str
    password: str = Field(min_length=8)
    email: str | None = None
    full_name: str | None = None


class TokenResponse(BaseModel):
    """Ответ с парой токенов после успешной аутентификации."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"  # noqa: S105
    expires_in: int  # срок жизни access токена в секундах


class RefreshRequest(BaseModel):
    """Запрос на обновление access токена через refresh токен."""

    refresh_token: str
