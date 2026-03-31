"""Сервис для MealEntry."""

from nutrition_tracking_api.api.crud.nutrition.meal_entry import MealEntryCRUD
from nutrition_tracking_api.api.schemas.nutrition.meal_entry import (
    MealEntryCreate,
    MealEntryDetailOut,
    MealEntryFilter,
    MealEntryOut,
    MealEntryUpdate,
)
from nutrition_tracking_api.api.services.base import BaseCRUDService


class MealEntryService(
    BaseCRUDService[
        MealEntryCRUD,
        MealEntryCreate,
        MealEntryUpdate,
        MealEntryDetailOut,
        MealEntryOut,
        MealEntryFilter,
    ]
):
    """Сервис для управления приёмами пищи."""

    create_model = MealEntryCreate
    update_model = MealEntryUpdate
    out_model = MealEntryDetailOut
    out_model_multi = MealEntryOut
    resource_crud_class = MealEntryCRUD
    filter_model = MealEntryFilter

    def _handle_pre_create(self, create_data: MealEntryCreate) -> None:
        """Инъекция user_id из токена аутентификации, если не передан явно."""
        if create_data.user_id is None:
            create_data.user_id = self.user_id
