"""MealEntry factory."""

import datetime

import factory

from nutrition_tracking_api.api.schemas.nutrition.meal_entry import (
    MealEntryCreate,
    MealTypeEnum,
)
from nutrition_tracking_api.orm.models.nutrition import MealEntry
from tests.factories.auth.user import UserFactory
from tests.factories.base import BaseMeta, BaseSQLAlchemyModelFactory


class MealEntryPayloadFactory(factory.Factory):
    """Фабрика для генерации MealEntryCreate схем (Pydantic)."""

    class Meta:
        model = MealEntryCreate

    user = factory.SubFactory(UserFactory)
    user_id = factory.SelfAttribute("user.id")
    date = factory.LazyFunction(datetime.date.today)
    meal_type = MealTypeEnum.lunch
    notes = None


class MealEntryFactory(MealEntryPayloadFactory, BaseSQLAlchemyModelFactory):
    """Фабрика для создания MealEntry ORM объектов в БД."""

    class Meta(BaseMeta):
        model = MealEntry
