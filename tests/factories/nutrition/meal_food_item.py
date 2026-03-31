"""MealFoodItem factory."""

import factory

from nutrition_tracking_api.api.schemas.nutrition.meal_food_item import MealFoodItemCreate
from nutrition_tracking_api.orm.models.nutrition import MealFoodItem
from tests.factories.base import BaseMeta, BaseSQLAlchemyModelFactory
from tests.factories.nutrition.meal_entry import MealEntryFactory


class MealFoodItemPayloadFactory(factory.Factory):
    """Фабрика для генерации MealFoodItemCreate схем (Pydantic)."""

    class Meta:
        model = MealFoodItemCreate

    meal_entry = factory.SubFactory(MealEntryFactory)
    meal_entry_id = factory.SelfAttribute("meal_entry.id")
    custom_name = factory.Sequence(lambda n: f"dish_{n}")
    amount_g = 100.0
    calories_kcal = 150.0
    protein_g = 10.0
    fat_g = 5.0
    carbs_g = 20.0


class MealFoodItemFactory(MealFoodItemPayloadFactory, BaseSQLAlchemyModelFactory):
    """Фабрика для создания MealFoodItem ORM объектов в БД."""

    class Meta(BaseMeta):
        model = MealFoodItem
