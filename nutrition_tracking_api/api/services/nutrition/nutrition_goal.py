"""Сервис для NutritionGoal."""

import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy.exc import NoResultFound

from nutrition_tracking_api.api.crud.nutrition.nutrition_goal import NutritionGoalCRUD
from nutrition_tracking_api.api.schemas.nutrition.nutrition_goal import (
    NutritionGoalCreate,
    NutritionGoalFilter,
    NutritionGoalOut,
    NutritionGoalUpdate,
)
from nutrition_tracking_api.api.services.base import BaseCRUDService

if TYPE_CHECKING:
    from nutrition_tracking_api.orm.models.nutrition import NutritionGoal


class NutritionGoalService(
    BaseCRUDService[
        NutritionGoalCRUD,
        NutritionGoalCreate,
        NutritionGoalUpdate,
        NutritionGoalOut,
        NutritionGoalOut,
        NutritionGoalFilter,
    ]
):
    """Сервис для управления целями по КБЖУ."""

    create_model = NutritionGoalCreate
    update_model = NutritionGoalUpdate
    out_model = NutritionGoalOut
    out_model_multi = NutritionGoalOut
    resource_crud_class = NutritionGoalCRUD
    filter_model = NutritionGoalFilter

    def get_active_goal(self) -> NutritionGoalOut | None:
        """Вернуть активную цель текущего пользователя (None если нет)."""
        try:
            goal = self.resource_crud.get_one_by_filter(
                {"user_id": self.user_id, "is_active": True},
                with_for_update=False,
            )
            return self.out_model.model_validate(goal)
        except NoResultFound:
            return None

    def _deactivate_current_goal(self) -> None:
        """Деактивировать текущую активную цель пользователя (если есть)."""
        try:
            active = self.resource_crud.get_one_by_filter(
                {"user_id": self.user_id, "is_active": True},
                with_for_update=True,
            )
        except NoResultFound:
            return
        self.update(active.id, NutritionGoalUpdate(is_active=False))

    def _handle_pre_create(self, create_data: NutritionGoalCreate) -> None:
        """Инжекция user_id и деактивация предыдущей активной цели."""
        if create_data.user_id is None:
            create_data.user_id = self.user_id
        self._deactivate_current_goal()

    def _handle_pre_update(
        self,
        resource_id: UUID,
        update_data: NutritionGoalUpdate,
    ) -> dict[str, Any]:
        """Валидация и авто-проставление ended_at при деактивации."""
        context = super()._handle_pre_update(resource_id, update_data)
        resource: NutritionGoal = context["resource"]

        if update_data.is_active is False and resource.is_active:
            update_data.ended_at = datetime.datetime.now().date()

        return context
