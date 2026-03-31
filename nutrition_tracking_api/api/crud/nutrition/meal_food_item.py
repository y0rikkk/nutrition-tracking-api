"""CRUD операции для MealFoodItem."""

from sqlalchemy.sql import Select

from nutrition_tracking_api.api.crud.base import BaseSyncCRUDOperations
from nutrition_tracking_api.orm.models.nutrition import MealFoodItem


class MealFoodItemCRUD(BaseSyncCRUDOperations[MealFoodItem]):
    """CRUD операции для модели MealFoodItem."""

    orm_model = MealFoodItem

    def _apply_joined_load(self, query: Select[tuple[MealFoodItem]]) -> Select[tuple[MealFoodItem]]:
        """JOIN на meal_entry нужен для RBAC matcher: meal_entry.user_id = $user.id."""
        return query.join(MealFoodItem.meal_entry)
