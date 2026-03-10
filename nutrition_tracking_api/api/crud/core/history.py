"""History CRUD operations."""

from sqlalchemy.orm import contains_eager
from sqlalchemy.sql import Select

from nutrition_tracking_api.api.crud.base import BaseSyncCRUDOperations
from nutrition_tracking_api.orm.models.auth import User
from nutrition_tracking_api.orm.models.core import History


class HistoryCRUD(BaseSyncCRUDOperations[History]):
    """CRUD операции для записей истории."""

    orm_model = History

    def _apply_joined_load(self, query: Select[tuple[History]]) -> Select[tuple[History]]:
        """Eagerly load user relationship."""
        return query.join(User, User.id == History.user_id, isouter=True).options(contains_eager(History.user))
