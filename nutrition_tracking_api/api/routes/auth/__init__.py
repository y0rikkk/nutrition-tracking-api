"""Auth router."""

from fastapi import APIRouter

from nutrition_tracking_api.api.routes.auth.policies import router as policies_router
from nutrition_tracking_api.api.routes.auth.roles import router as roles_router
from nutrition_tracking_api.api.routes.auth.users import router as user_router

auth_router = APIRouter(prefix="/auth")
auth_router.include_router(user_router)
auth_router.include_router(roles_router)
auth_router.include_router(policies_router)
