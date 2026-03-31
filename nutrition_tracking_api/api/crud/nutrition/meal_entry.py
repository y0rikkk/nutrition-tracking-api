"""CRUD операции для MealEntry."""

from sqlalchemy import Select
from sqlalchemy.orm import subqueryload

from nutrition_tracking_api.api.crud.base import BaseSyncCRUDOperations
from nutrition_tracking_api.orm.models.nutrition import MealEntry


class MealEntryCRUD(BaseSyncCRUDOperations[MealEntry]):
    """CRUD операции для модели MealEntry."""

    orm_model = MealEntry

    def _apply_joined_load(self, query: Select) -> Select:
        """Загружать items для расчёта агрегатов и детального просмотра."""
        return query.options(subqueryload(MealEntry.items))
