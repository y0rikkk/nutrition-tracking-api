"""CRUD операции для FoodItem."""

from sqlalchemy.orm import joinedload
from sqlalchemy.sql import Select

from nutrition_tracking_api.api.crud.base import BaseSyncCRUDOperations
from nutrition_tracking_api.orm.models.nutrition import FoodItem


class FoodItemCRUD(BaseSyncCRUDOperations[FoodItem]):
    """CRUD операции для модели FoodItem."""

    orm_model = FoodItem

    def _apply_joined_load(self, query: Select[tuple[FoodItem]]) -> Select[tuple[FoodItem]]:
        return query.options(
            joinedload(FoodItem.creator),
            joinedload(FoodItem.modifier),
        )
