"""Role factory."""

import factory

from nutrition_tracking_api.api.schemas.auth.roles import RoleCreate
from nutrition_tracking_api.orm.models.auth import Role
from tests.factories.base import BaseMeta, BaseSQLAlchemyModelFactory


class RolePayloadFactory(factory.Factory):
    """Фабрика для генерации RoleCreate схем."""

    class Meta:
        model = RoleCreate

    name = factory.Sequence(lambda n: f"role_{n}")
    description = factory.Faker("word")
    is_default = False


class RoleFactory(RolePayloadFactory, BaseSQLAlchemyModelFactory):
    """Фабрика для создания Role ORM объектов."""

    class Meta(BaseMeta):
        model = Role
