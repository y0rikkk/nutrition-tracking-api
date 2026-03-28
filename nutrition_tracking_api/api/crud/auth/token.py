"""Refresh token CRUD operations."""

from sqlalchemy.exc import NoResultFound

from nutrition_tracking_api.api.crud.base import BaseSyncCRUDOperations
from nutrition_tracking_api.orm.models.token import RefreshToken


class RefreshTokenCRUD(BaseSyncCRUDOperations[RefreshToken]):
    """CRUD операции для refresh токенов."""

    orm_model = RefreshToken

    def get_by_jti(self, jti: str) -> RefreshToken:
        """
        Найти refresh токен по JWT ID.

        Args:
        ----
            jti: Уникальный идентификатор токена

        Returns:
        -------
            ORM объект RefreshToken

        Raises:
        ------
            NoResultFound: Если токен не найден

        """
        return self.get_one_by_filter({"jti": jti}, with_for_update=False)

    def revoke_by_jti(self, jti: str) -> None:
        """
        Отозвать refresh токен по JWT ID.

        Args:
        ----
            jti: Уникальный идентификатор токена

        """
        try:
            token = self.get_by_jti(jti)
            self.update(token.id, {"is_revoked": True})
        except NoResultFound:
            pass  # Токен уже не существует — ничего не делаем
