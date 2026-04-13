"""Сервис для MealFoodItem."""

from nutrition_tracking_api.api.crud.nutrition.food_item import FoodItemCRUD
from nutrition_tracking_api.api.crud.nutrition.meal_food_item import MealFoodItemCRUD
from nutrition_tracking_api.api.schemas.nutrition.meal_food_item import (
    MealFoodItemCreate,
    MealFoodItemFilter,
    MealFoodItemOut,
    MealFoodItemUpdate,
)
from nutrition_tracking_api.api.services.base import BaseCRUDService


class MealFoodItemService(
    BaseCRUDService[
        MealFoodItemCRUD,
        MealFoodItemCreate,
        MealFoodItemUpdate,
        MealFoodItemOut,
        MealFoodItemOut,
        MealFoodItemFilter,
    ]
):
    """Сервис для управления продуктами в приёмах пищи."""

    create_model = MealFoodItemCreate
    update_model = MealFoodItemUpdate
    out_model = MealFoodItemOut
    out_model_multi = MealFoodItemOut
    resource_crud_class = MealFoodItemCRUD
    filter_model = MealFoodItemFilter

    def _handle_pre_create(self, create_data: MealFoodItemCreate) -> None:
        """Авто-расчёт КБЖУ и подстановка названия из FoodItem если food_item_id указан."""
        if create_data.food_item_id is not None:
            food_item = FoodItemCRUD(self.resource_crud.session).get(create_data.food_item_id, with_for_update=False)
            factor = create_data.amount_g / 100
            create_data.name = food_item.name
            create_data.calories_kcal = round(food_item.calories_per_100g * factor, 2)
            create_data.protein_g = round(food_item.protein_per_100g * factor, 2)
            create_data.fat_g = round(food_item.fat_per_100g * factor, 2)
            create_data.carbs_g = round(food_item.carbs_per_100g * factor, 2)
