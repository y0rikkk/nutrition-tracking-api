"""User CRUD operations."""

from typing import Any

from sqlalchemy import ColumnClause
from sqlalchemy.orm import InstrumentedAttribute
from sqlalchemy.sql import Select

from nutrition_tracking_api.api.crud.base import BaseSyncCRUDOperations
from nutrition_tracking_api.orm.models.auth import Role, User


class UserCRUD(BaseSyncCRUDOperations[User]):
    """CRUD операции для пользователей."""

    orm_model = User

    def _get_filtered_column(self, field_name: str) -> InstrumentedAttribute[Any] | ColumnClause[Any]:
        """Маппинг имён фильтров на колонки связанных таблиц."""
        match field_name:
            case "role_id":
                return Role.id
            case "role_name":
                return Role.name
        return super()._get_filtered_column(field_name)

    def _apply_joined_load(self, query: Select[tuple[User]]) -> Select[tuple[User]]:
        """JOIN'ы необходимые для работы фильтров и eager loading roles."""
        return query.join(User.roles, isouter=True).distinct()
