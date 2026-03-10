"""History service."""

from nutrition_tracking_api.api.crud.core.history import HistoryCRUD
from nutrition_tracking_api.api.schemas.core.history import HistoryCreate, HistoryFilter, HistoryOut
from nutrition_tracking_api.api.services.base import BaseCRUDService


class HistoryService(
    BaseCRUDService[
        HistoryCRUD,
        HistoryCreate,
        HistoryCreate,
        HistoryOut,
        HistoryOut,
        HistoryFilter,
    ]
):
    """Сервис для работы с историей изменений."""

    create_model = HistoryCreate
    update_model = HistoryCreate
    out_model = HistoryOut
    out_model_multi = HistoryOut
    resource_crud_class = HistoryCRUD
    filter_model = HistoryFilter
