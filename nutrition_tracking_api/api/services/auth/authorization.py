"""Сервис верификации токенов и проверки прав доступа."""

from datetime import datetime

from fastapi import Request
from jwt.exceptions import InvalidSignatureError
from sqlalchemy.exc import NoResultFound

from nutrition_tracking_api.api.exceptions import AuthTokenExpiredError, AuthTokenValidateError
from nutrition_tracking_api.api.schemas.auth.common import SecretConfig
from nutrition_tracking_api.api.schemas.auth.user import UserCreate
from nutrition_tracking_api.api.services.auth.permissions import PermissionService
from nutrition_tracking_api.api.services.auth.users import UserService
from nutrition_tracking_api.api.utils.auth import get_jwt_token_header_mapping, get_user_data_from_jwt_token
from nutrition_tracking_api.integrations.twork import get_secret_config
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
        Верифицировать JWT токен.

        1. Ищем пользователя по токену в БД
        2. Проверяем срок действия токена
        3. Если нет в БД → декодируем TWork JWT → создаём/обновляем User

        Args:
        ----
            access_token: Bearer JWT токен

        Returns:
        -------
            ORM объект пользователя

        Raises:
        ------
            AuthTokenExpiredError: Если токен истек
            AuthTokenValidateError: Если токен невалиден

        """
        try:
            user = self.users_service.get_by_token(access_token)
            if user.access_token_expires_at and user.access_token_expires_at <= datetime.now(
                tz=user.access_token_expires_at.tzinfo
            ):
                raise AuthTokenExpiredError
        except NoResultFound:
            decoded_user = self.get_decoded_user_from_twork_jwt_token(access_token)
            user = self.users_service.create_or_update(decoded_user)
        return user

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

    def verify_service_token(self, request: Request, service_token: str) -> bool:
        """
        Верифицировать service-to-service токен.

        Args:
        ----
            request: FastAPI Request
            service_token: Сервисный токен из заголовка XXX-Token-Authorization

        Returns:
        -------
            True если доступ разрешен

        Raises:
        ------
            AuthTokenValidateError: Если токен невалиден или нет прав

        """
        try:
            service_user = self.users_service.get_by_token(service_token)
            if service_user.is_superuser or (
                service_user.is_service_user
                and self.permission_service.validate_path_permissions(
                    user=service_user,
                    path=request.url.path,
                    method=request.method,
                    request=request,
                )
            ):
                self._set_request_state(request, service_user)
                return True
        except NoResultFound as e:
            raise AuthTokenValidateError from e
        raise AuthTokenValidateError

    @staticmethod
    def get_secret_key_by_jwt_token_header(
        jwt_token_header: dict[str, str], secret_config: list[SecretConfig]
    ) -> SecretConfig:
        """
        Найти подходящий публичный ключ по заголовку JWT.

        Args:
        ----
            jwt_token_header: Заголовок JWT (alg, kid)
            secret_config: Список ключей из JWKS

        Returns:
        -------
            Подходящий SecretConfig

        Raises:
        ------
            AuthTokenValidateError: Если ключ не найден

        """
        for key in secret_config:
            if key.alg == jwt_token_header.get("alg") and key.kid == jwt_token_header.get("kid"):
                return key
        raise AuthTokenValidateError

    def get_decoded_user_from_twork_jwt_token(self, access_token: str) -> UserCreate:
        """
        Декодировать TWork JWT токен и вернуть UserCreate схему.

        Args:
        ----
            access_token: JWT токен

        Returns:
        -------
            UserCreate схема с данными пользователя

        Raises:
        ------
            AuthTokenValidateError: Если токен невалиден или ключ не найден

        """
        token_header = get_jwt_token_header_mapping(access_token)
        try:
            secret_config = get_secret_config()
            secret_key = self.get_secret_key_by_jwt_token_header(token_header, secret_config)
            return get_user_data_from_jwt_token(access_token, secret_key)
        except (AuthTokenValidateError, InvalidSignatureError) as e:
            raise AuthTokenValidateError from e
