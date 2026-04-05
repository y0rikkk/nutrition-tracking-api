"""User factory."""

import datetime

import factory

from nutrition_tracking_api.api.schemas.auth import UserCreate
from nutrition_tracking_api.api.schemas.auth.user import ActivityLevelEnum, GenderEnum
from nutrition_tracking_api.api.utils.auth import create_access_token
from nutrition_tracking_api.orm.models.auth import User
from tests.factories.base import BaseMeta, BaseSQLAlchemyModelFactory


class UserPayloadFactory(factory.Factory):
    """Фабрика для генерации UserCreate схем."""

    class Meta:
        model = UserCreate

    username = factory.Sequence(lambda n: f"test_user_{n}")
    is_superuser = False
    email = factory.Faker("email")
    birth_date = datetime.date(1990, 1, 1)
    gender = GenderEnum.male
    height_cm = 175.0
    weight_kg = 70.0
    activity_level = ActivityLevelEnum.moderately_active


class UserFactory(UserPayloadFactory, BaseSQLAlchemyModelFactory):
    """Фабрика для создания User ORM объектов в БД.

    После создания добавляет `access_token` как Python-атрибут (не хранится в БД):
    - Удобно в тестах: `user.access_token` → валидный Bearer токен
    - verify_jwt_token декодирует его, извлекает user_id (sub), загружает User из БД
    """

    class Meta(BaseMeta):
        model = User

    @classmethod
    def _after_postgeneration(cls, instance: User, create: bool, results: dict | None = None) -> None:
        """Добавить JWT access_token как Python-атрибут после создания объекта."""
        super()._after_postgeneration(instance, create, results)
        instance.access_token = create_access_token(str(instance.id), instance.username)  # type: ignore[attr-defined]
