"""CRUD операции для WeightLog."""

from nutrition_tracking_api.api.crud.base import BaseSyncCRUDOperations
from nutrition_tracking_api.orm.models.nutrition import WeightLog


class WeightLogCRUD(BaseSyncCRUDOperations[WeightLog]):
    """CRUD операции для модели WeightLog."""

    orm_model = WeightLog
