"""Auth routes для политик доступа."""

from fastapi import APIRouter

from nutrition_tracking_api.api.services.auth.policy import PolicyService
from nutrition_tracking_api.api.utils.routes import init_crud_routes

router = APIRouter(tags=["policy"], prefix="/policies")

init_crud_routes(router, PolicyService)
