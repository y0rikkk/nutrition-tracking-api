"""Публичные endpoints аутентификации (без validate_token)."""

import contextlib
from http import HTTPStatus

from fastapi import APIRouter

from nutrition_tracking_api.api.exceptions import AuthTokenExpiredError, AuthTokenValidateError
from nutrition_tracking_api.api.schemas.auth.token import LoginRequest, RefreshRequest, RegisterRequest, TokenResponse
from nutrition_tracking_api.api.services.auth.token import TokenService
from nutrition_tracking_api.dependencies import SessionDependency

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register/", status_code=HTTPStatus.CREATED)
def register(data: RegisterRequest, session: SessionDependency) -> TokenResponse:
    """Публичный endpoint — авторизация не требуется."""
    return TokenService(session).register(data)


@router.post("/login/")
def login(data: LoginRequest, session: SessionDependency) -> TokenResponse:
    """Публичный endpoint — авторизация не требуется."""
    return TokenService(session).login(data)


@router.post("/token/refresh/")
def refresh_token(data: RefreshRequest, session: SessionDependency) -> TokenResponse:
    """Публичный endpoint — авторизация не требуется."""
    return TokenService(session).refresh(data.refresh_token)


@router.post("/logout/", status_code=HTTPStatus.NO_CONTENT)
def logout(data: RefreshRequest, session: SessionDependency) -> None:
    """Публичный endpoint — авторизация не требуется."""
    # Если уже истёк или невалиден — логаут считается успешным
    with contextlib.suppress(AuthTokenExpiredError, AuthTokenValidateError):
        TokenService(session).revoke(data.refresh_token)
