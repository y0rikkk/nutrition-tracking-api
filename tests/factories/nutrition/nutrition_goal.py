"""NutritionGoal factory."""

import datetime

import factory

from nutrition_tracking_api.api.schemas.nutrition.nutrition_goal import NutritionGoalCreate
from nutrition_tracking_api.orm.models.nutrition import NutritionGoal
from tests.factories.auth.user import UserFactory
from tests.factories.base import BaseMeta, BaseSQLAlchemyModelFactory


class NutritionGoalPayloadFactory(factory.Factory):
    """Фабрика для генерации NutritionGoalCreate схем (Pydantic)."""

    class Meta:
        model = NutritionGoalCreate

    user = factory.SubFactory(UserFactory)
    user_id = factory.SelfAttribute("user.id")
    calories_kcal = 2000.0
    protein_g = 150.0
    fat_g = 70.0
    carbs_g = 250.0
    started_at = factory.LazyFunction(datetime.date.today)
    notes = None


class NutritionGoalFactory(NutritionGoalPayloadFactory, BaseSQLAlchemyModelFactory):
    """Фабрика для создания NutritionGoal ORM объектов в БД."""

    class Meta(BaseMeta):
        model = NutritionGoal

    is_active = True
    ended_at = None
