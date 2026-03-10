"""Policy factory."""

import factory

from nutrition_tracking_api.api.schemas.auth.policies import PolicyCreate
from nutrition_tracking_api.orm.models.auth import Policy
from tests.factories.base import BaseMeta, BaseSQLAlchemyModelFactory


class PolicyPayloadFactory(factory.Factory):
    """Фабрика для генерации PolicyCreate схем."""

    class Meta:
        model = PolicyCreate

    name = factory.Sequence(lambda n: f"policy_{n}")
    description = factory.Faker("word")
    targets = factory.List(["/auth/users/", "/auth/users/{object_id}"])
    actions = factory.List(["GET", "POST", "PATCH", "DELETE"])
    matchers = None
    options = None


class PolicyFactory(PolicyPayloadFactory, BaseSQLAlchemyModelFactory):
    """Фабрика для создания Policy ORM объектов."""

    class Meta(BaseMeta):
        model = Policy
