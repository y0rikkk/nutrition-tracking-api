"""Core router."""

from fastapi import APIRouter

from nutrition_tracking_api.api.routes.core.history import router as history_router

core_router = APIRouter(prefix="/core")
core_router.include_router(history_router)
