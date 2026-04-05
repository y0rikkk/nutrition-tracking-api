"""User factory."""

import datetime

import factory

from nutrition_tracking_api.api.schemas.auth import UserCreate
from nutrition_tracking_api.api.schemas.auth.user import ActivityLevelEnum, GenderEnum
from nutrition_tracking_api.api.utils.auth import create_access_token, hash_password
from nutrition_tracking_api.orm.models.auth import User
from tests.factories.base import BaseMeta, BaseSQLAlchemyModelFactory


class UserPayloadFactory(factory.Factory):
    """Фабрика для генерации UserCreate схем."""

    class Meta:
        model = UserCreate

    username = factory.Sequence(lambda n: f"test_user_{n}")
    access_token = None  # Для обычных пользователей не используется (JWT stateless)
    is_superuser = False
    is_service_user = False
    email = factory.Faker("email")
    birth_date = datetime.date(1990, 1, 1)
    gender = GenderEnum.male
    height_cm = 175.0
    weight_kg = 70.0
    activity_level = ActivityLevelEnum.moderately_active


class UserFactory(UserPayloadFactory, BaseSQLAlchemyModelFactory):
    """Фабрика для создания User ORM объектов в БД.

    Генерирует валидный HS256 JWT и сохраняет в access_token для удобства тестов:
    - verify_jwt_token декодирует токен, извлекает user_id (sub), загружает User из БД
    - Так тесты могут использовать user.access_token как Bearer токен в Authorization header
    """

    class Meta(BaseMeta):
        model = User

    # Генерировать валидный HS256 JWT, чтобы тесты могли делать Bearer-запросы
    access_token = factory.LazyAttribute(lambda obj: create_access_token(str(obj.id), obj.username))  # type: ignore[assignment]
    # Пароль по умолчанию для тестовых пользователей
    password_hash = factory.LazyFunction(lambda: hash_password("testpassword123"))
