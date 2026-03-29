"""Роуты для FoodItem."""

from fastapi import APIRouter

from nutrition_tracking_api.api.services.nutrition.food_item import FoodItemService
from nutrition_tracking_api.api.utils.routes import init_crud_routes

router = APIRouter(tags=["food_items"], prefix="/foods")

init_crud_routes(router, FoodItemService)
