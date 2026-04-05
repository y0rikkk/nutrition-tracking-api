"""Сервис верификации токенов и проверки прав доступа."""

import uuid

from fastapi import Request
from sqlalchemy.exc import NoResultFound

from nutrition_tracking_api.api.exceptions import AuthTokenValidateError
from nutrition_tracking_api.api.services.auth.permissions import PermissionService
from nutrition_tracking_api.api.services.auth.users import UserService
from nutrition_tracking_api.api.utils.auth import decode_token
from nutrition_tracking_api.orm.models.auth import User


class AuthService:
    """Сервис для аутентификации и авторизации."""

    def __init__(
        self,
        users_service: UserService,
        permission_service: PermissionService,
    ) -> None:
        self.permission_service = permission_service
        self.users_service = users_service

    def verify_jwt_token(self, access_token: str) -> User:
        """
        Верифицировать наш JWT access токен (HS256).

        1. Декодируем токен (проверяем подпись и срок жизни)
        2. Проверяем что type == "access"
        3. Загружаем пользователя из БД по user_id (sub)

        Args:
        ----
            access_token: Bearer JWT токен

        Returns:
        -------
            ORM объект пользователя

        Raises:
        ------
            AuthTokenExpiredError: Если токен истёк
            AuthTokenValidateError: Если токен невалиден

        """
        payload = decode_token(access_token)  # Выбрасывает AuthTokenExpiredError / AuthTokenValidateError

        if payload.get("type") != "access":
            raise AuthTokenValidateError

        try:
            user_id = payload["sub"]
            return self.users_service.resource_crud.get_one_by_filter({"id": uuid.UUID(user_id)}, with_for_update=False)
        except (KeyError, ValueError, NoResultFound) as e:
            raise AuthTokenValidateError from e

    def _set_request_state(self, request: Request, user: User) -> None:
        """Сохранить пользователя и данные в request.state."""
        request.state.user = user
        if getattr(request.state, "log_payload", None):
            request.state.log_payload.update({"user_id": str(user.id), "username": user.username})
        else:
            request.state.log_payload = {"user_id": str(user.id), "username": user.username}

    def verify_permissions(self, request: Request, access_token: str) -> bool:
        """
        Верифицировать токен и проверить права доступа.

        Endpoint /auth/users/me/ доступен без проверки прав.

        Args:
        ----
            request: FastAPI Request
            access_token: Bearer токен

        Returns:
        -------
            True если доступ разрешен

        """
        user = self.verify_jwt_token(access_token)
        self._set_request_state(request, user)

        # Endpoint /auth/users/me/ доступен без проверки прав
        if request.url.path == "/auth/users/me/" and request.method == "GET":
            return True

        return self.permission_service.validate_path_permissions(
            user=user, path=request.url.path, method=request.method, request=request
        )
