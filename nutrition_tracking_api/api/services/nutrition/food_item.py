"""Сервис для FoodItem."""

from nutrition_tracking_api.api.crud.nutrition.food_item import FoodItemCRUD
from nutrition_tracking_api.api.schemas.nutrition.food_item import (
    FoodItemCreate,
    FoodItemFilter,
    FoodItemOut,
    FoodItemUpdate,
)
from nutrition_tracking_api.api.services.base import BaseCRUDService


class FoodItemService(
    BaseCRUDService[
        FoodItemCRUD,
        FoodItemCreate,
        FoodItemUpdate,
        FoodItemOut,
        FoodItemOut,
        FoodItemFilter,
    ]
):
    """Сервис для управления продуктами питания."""

    create_model = FoodItemCreate
    update_model = FoodItemUpdate
    out_model = FoodItemOut
    out_model_multi = FoodItemOut
    resource_crud_class = FoodItemCRUD
    filter_model = FoodItemFilter
    track_history = True
