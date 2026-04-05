"""Сервис для WeightLog."""

from nutrition_tracking_api.api.crud.nutrition.weight_log import WeightLogCRUD
from nutrition_tracking_api.api.schemas.nutrition.weight_log import (
    WeightLogCreate,
    WeightLogFilter,
    WeightLogOut,
    WeightLogUpdate,
)
from nutrition_tracking_api.api.services.base import BaseCRUDService


class WeightLogService(
    BaseCRUDService[
        WeightLogCRUD,
        WeightLogCreate,
        WeightLogUpdate,
        WeightLogOut,
        WeightLogOut,
        WeightLogFilter,
    ]
):
    """Сервис для управления записями веса."""

    create_model = WeightLogCreate
    update_model = WeightLogUpdate
    out_model = WeightLogOut
    out_model_multi = WeightLogOut
    resource_crud_class = WeightLogCRUD
    filter_model = WeightLogFilter

    def get_latest(self) -> WeightLogOut | None:
        """Вернуть последнюю запись веса пользователя (по дате, затем по времени создания)."""
        results = self.resource_crud.get_multi(
            {"user_id": self.user_id},
            with_for_update=False,
        )
        if not results:
            return None
        latest = sorted(results, key=lambda w: (w.date, w.created_at), reverse=True)[0]
        return self.out_model.model_validate(latest)

    def _handle_pre_create(self, create_data: WeightLogCreate) -> None:
        """Инжекция user_id из токена, если не передан явно."""
        if create_data.user_id is None:
            create_data.user_id = self.user_id
