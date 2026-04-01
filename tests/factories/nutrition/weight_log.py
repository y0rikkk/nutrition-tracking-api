"""WeightLog factory."""

import datetime

import factory

from nutrition_tracking_api.api.schemas.nutrition.weight_log import WeightLogCreate
from nutrition_tracking_api.orm.models.nutrition import WeightLog
from tests.factories.auth.user import UserFactory
from tests.factories.base import BaseMeta, BaseSQLAlchemyModelFactory


class WeightLogPayloadFactory(factory.Factory):
    """Фабрика для генерации WeightLogCreate схем (Pydantic)."""

    class Meta:
        model = WeightLogCreate

    user = factory.SubFactory(UserFactory)
    user_id = factory.SelfAttribute("user.id")
    date = factory.LazyFunction(datetime.date.today)
    weight_kg = 75.0
    notes = None


class WeightLogFactory(WeightLogPayloadFactory, BaseSQLAlchemyModelFactory):
    """Фабрика для создания WeightLog ORM объектов в БД."""

    class Meta(BaseMeta):
        model = WeightLog
