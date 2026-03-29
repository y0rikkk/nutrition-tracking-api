"""FoodItem factory."""

import factory

from nutrition_tracking_api.api.schemas.nutrition.food_item import FoodItemCreate
from nutrition_tracking_api.orm.models.nutrition import FoodItem
from tests.factories.base import BaseMeta, BaseSQLAlchemyModelFactory


class FoodItemPayloadFactory(factory.Factory):
    """Фабрика для генерации FoodItemCreate схем (Pydantic)."""

    class Meta:
        model = FoodItemCreate

    name = factory.Sequence(lambda n: f"food_{n}")
    brand = None
    calories_per_100g = 100.0
    protein_per_100g = 10.0
    fat_per_100g = 5.0
    carbs_per_100g = 15.0
    barcode = None


class FoodItemFactory(FoodItemPayloadFactory, BaseSQLAlchemyModelFactory):
    """Фабрика для создания FoodItem ORM объектов в БД."""

    class Meta(BaseMeta):
        model = FoodItem
