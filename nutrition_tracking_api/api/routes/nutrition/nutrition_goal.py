"""Роуты для NutritionGoal."""

from fastapi import APIRouter

from nutrition_tracking_api.api.services.nutrition.nutrition_goal import NutritionGoalService
from nutrition_tracking_api.api.utils.routes import init_crud_routes

router = APIRouter(tags=["nutrition_goals"], prefix="/goals")

init_crud_routes(router, NutritionGoalService)
