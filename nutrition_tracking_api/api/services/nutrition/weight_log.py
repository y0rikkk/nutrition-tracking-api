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

    def _handle_pre_create(self, create_data: WeightLogCreate) -> None:
        """Инжекция user_id из токена, если не передан явно."""
        if create_data.user_id is None:
            create_data.user_id = self.user_id
