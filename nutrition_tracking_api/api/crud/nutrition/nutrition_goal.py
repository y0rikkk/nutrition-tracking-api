"""CRUD операции для NutritionGoal."""

from nutrition_tracking_api.api.crud.base import BaseSyncCRUDOperations
from nutrition_tracking_api.orm.models.nutrition import NutritionGoal


class NutritionGoalCRUD(BaseSyncCRUDOperations[NutritionGoal]):
    """CRUD операции для модели NutritionGoal."""

    orm_model = NutritionGoal
