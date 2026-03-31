"""Роуты для MealFoodItem."""

from fastapi import APIRouter

from nutrition_tracking_api.api.services.nutrition.meal_food_item import MealFoodItemService
from nutrition_tracking_api.api.utils.routes import init_crud_routes

router = APIRouter(tags=["meal_food_items"], prefix="/meal-items")

init_crud_routes(router, MealFoodItemService)
