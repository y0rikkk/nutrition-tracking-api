"""Сервис для MealEntry."""

import datetime

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

    def get_daily_meals(self, date: datetime.date) -> list[MealEntryDetailOut]:
        """Получить приёмы пищи с составом за день.

        Использует out_model (MealEntryDetailOut с items), а не out_model_multi,
        поэтому реализован отдельным методом а не через стандартный get_multi.
        """
        resources = self.resource_crud.get_multi(
            {"user_id": self.user_id, "date": date},
            with_for_update=False,
        )
        return [self.out_model.model_validate(r) for r in resources]

    def _handle_pre_create(self, create_data: MealEntryCreate) -> None:
        """Инъекция user_id из токена аутентификации, если не передан явно."""
        if create_data.user_id is None:
            create_data.user_id = self.user_id
