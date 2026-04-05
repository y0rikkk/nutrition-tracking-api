"""Auth dependencies — извлечение токенов из headers."""

from fastapi import Depends, Request
from fastapi.exceptions import HTTPException
from fastapi.openapi.models import SecurityBase as OpenApiSecurityBase
from fastapi.openapi.models import SecuritySchemeType
from fastapi.security.base import SecurityBase
from fastapi.security.utils import get_authorization_scheme_param
from starlette.status import HTTP_401_UNAUTHORIZED

from nutrition_tracking_api.api.services.auth.authorization import AuthService
from nutrition_tracking_api.api.services.auth.permissions import PermissionService
from nutrition_tracking_api.api.services.auth.users import UserService
from nutrition_tracking_api.dependencies import SessionDependency


class AuthToken(SecurityBase):
    """Bearer token из заголовка Authorization: Bearer <jwt>."""

    def __init__(self, *, scheme_name: str | None = None) -> None:
        self.scheme_name = scheme_name or self.__class__.__name__
        self.model = OpenApiSecurityBase(type=SecuritySchemeType.http)

    def __call__(self, request: Request) -> str | None:
        sso_auth_token: str | None = request.headers.get("Authorization")
        if sso_auth_token:
            scheme, param = get_authorization_scheme_param(sso_auth_token)
            if scheme.lower() == "bearer":
                return param
        return None


auth_token_obtain = AuthToken()


def auth_service_dependency(db_session: SessionDependency) -> AuthService:
    """
    Dependency для создания AuthService.

    Args:
    ----
        db_session: Database session

    Returns:
    -------
        AuthService instance

    """
    return AuthService(
        users_service=UserService(db_session),
        permission_service=PermissionService(),
    )


def validate_token(
    request: Request,
    auth_token: str | None = Depends(auth_token_obtain),
    auth_service: AuthService = Depends(auth_service_dependency),
) -> bool:
    """
    Главная dependency для аутентификации.

    Args:
    ----
        request: FastAPI Request
        auth_token: Bearer JWT токен (или None)
        auth_service: AuthService instance

    Returns:
    -------
        True если аутентификация успешна

    Raises:
    ------
        HTTPException 401: Если аутентификация не прошла

    """
    if auth_token and auth_service.verify_permissions(request, auth_token):
        return True

    raise HTTPException(
        status_code=HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )
