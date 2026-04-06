"""Роуты домена nutrition."""

from fastapi import APIRouter

from nutrition_tracking_api.api.routes.nutrition import (
    advice,
    dashboard,
    food_item,
    meal_entry,
    meal_food_item,
    nutrition_goal,
    weight_log,
)

nutrition_router = APIRouter()
nutrition_router.include_router(advice.router)
nutrition_router.include_router(dashboard.router)
nutrition_router.include_router(food_item.router)
nutrition_router.include_router(meal_entry.router)
nutrition_router.include_router(meal_food_item.router)
nutrition_router.include_router(nutrition_goal.router)
nutrition_router.include_router(weight_log.router)
