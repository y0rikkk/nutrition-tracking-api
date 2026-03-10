"""History routes."""

from fastapi import APIRouter

from nutrition_tracking_api.api.services.history import HistoryService
from nutrition_tracking_api.api.utils.routes import ExcludeRoutersEnum, init_crud_routes

router = APIRouter(tags=["history"], prefix="/history")

init_crud_routes(
    router,
    HistoryService,
    exclude_routes={ExcludeRoutersEnum.CREATE, ExcludeRoutersEnum.UPDATE, ExcludeRoutersEnum.DELETE},
)
