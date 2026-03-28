"""Сервис для управления JWT токенами (выдача, обновление, отзыв)."""

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from nutrition_tracking_api.api.crud.auth.token import RefreshTokenCRUD
from nutrition_tracking_api.api.crud.auth.user import UserCRUD
from nutrition_tracking_api.api.exceptions import AuthTokenExpiredError, AuthTokenValidateError
from nutrition_tracking_api.api.schemas.auth.token import LoginRequest, RegisterRequest, TokenResponse
from nutrition_tracking_api.api.services.auth.users import UserService
from nutrition_tracking_api.api.utils.auth import create_access_token, create_refresh_token, decode_token
from nutrition_tracking_api.orm.models.auth import User
from nutrition_tracking_api.settings import settings


class TokenService:
    """Сервис для выдачи, обновления и отзыва JWT токенов."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.refresh_crud = RefreshTokenCRUD(session)
        self.user_crud = UserCRUD(session)

    def register(self, data: RegisterRequest) -> TokenResponse:
        """Зарегистрировать нового пользователя и выдать пару токенов."""
        user = UserService(self.session).create_with_password(
            username=data.username,
            password=data.password,
            email=data.email,
            full_name=data.full_name,
        )
        return self.issue_tokens(user)

    def login(self, data: LoginRequest) -> TokenResponse:
        """Аутентифицировать пользователя по логину/паролю и выдать пару токенов."""
        user = UserService(self.session).authenticate(data.username, data.password)
        return self.issue_tokens(user)

    def issue_tokens(self, user: User) -> TokenResponse:
        """
        Выдать пару токенов (access + refresh) для пользователя.

        Сохраняет refresh токен (jti) в БД для возможности отзыва.

        Args:
        ----
            user: ORM объект пользователя

        Returns:
        -------
            TokenResponse с access_token, refresh_token, expires_in

        """
        access_token = create_access_token(str(user.id), user.username)
        refresh_token_str, jti = create_refresh_token(str(user.id))

        expires_at = datetime.now(tz=timezone.utc) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
        self.refresh_crud.create(
            {
                "user_id": user.id,
                "jti": jti,
                "expires_at": expires_at,
                "is_revoked": False,
            }
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token_str,
            expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    def refresh(self, refresh_token: str) -> TokenResponse:
        """
        Обменять refresh токен на новую пару токенов (token rotation).

        Старый refresh токен отзывается, выдаётся новая пара.

        Args:
        ----
            refresh_token: Текущий refresh токен

        Returns:
        -------
            Новый TokenResponse

        Raises:
        ------
            AuthTokenExpiredError: Если токен истёк
            AuthTokenValidateError: Если токен невалиден или уже отозван

        """
        payload = decode_token(refresh_token)  # Выбрасывает AuthTokenExpiredError / AuthTokenValidateError

        if payload.get("type") != "refresh":
            raise AuthTokenValidateError

        jti = payload.get("jti")
        if not jti:
            raise AuthTokenValidateError

        db_token = self.refresh_crud.get_by_jti(jti)
        if db_token.is_revoked:
            raise AuthTokenExpiredError

        # Token rotation — отзываем старый refresh токен
        self.refresh_crud.update(db_token.id, {"is_revoked": True})

        user = self.user_crud.get(UUID(payload["sub"]), with_for_update=False)
        return self.issue_tokens(user)

    def revoke(self, refresh_token: str) -> None:
        """
        Отозвать refresh токен (logout).

        Args:
        ----
            refresh_token: Refresh токен для отзыва

        Raises:
        ------
            AuthTokenExpiredError: Если токен истёк
            AuthTokenValidateError: Если токен невалиден

        """
        payload = decode_token(refresh_token)

        if payload.get("type") != "refresh":
            raise AuthTokenValidateError

        jti = payload.get("jti")
        if jti:
            self.refresh_crud.revoke_by_jti(jti)
