"""Роуты для WeightLog."""

from fastapi import APIRouter

from nutrition_tracking_api.api.services.nutrition.weight_log import WeightLogService
from nutrition_tracking_api.api.utils.routes import init_crud_routes

router = APIRouter(tags=["weight_logs"], prefix="/weight-logs")

init_crud_routes(router, WeightLogService)
