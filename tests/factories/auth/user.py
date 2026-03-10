"""User factory."""

import json
from datetime import datetime, timedelta, timezone

import factory
import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm

from nutrition_tracking_api.api.schemas.auth import UserCreate
from nutrition_tracking_api.api.schemas.auth.common import SecretConfig
from nutrition_tracking_api.orm.models.auth import User
from tests.factories.base import BaseMeta, BaseSQLAlchemyModelFactory

TEST_NOT_SERVICE_USER_MAPPING: dict[str, str] = {
    "uname": "test",
    "ad_login": "test",
    "master_id": "123456",
}

# Тестовые RSA-ключи: подписываем токен приватным, верифицируем публичным
_test_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_test_wrong_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)


def _make_secret_config(private_key: rsa.RSAPrivateKey) -> SecretConfig:
    jwk_dict = json.loads(RSAAlgorithm.to_jwk(private_key.public_key()))
    return SecretConfig(kty=jwk_dict["kty"], use="sig", kid="TWork", n=jwk_dict["n"], e=jwk_dict["e"], alg="RS256")


# Правильный PublicKey (совпадает с _test_private_key) — для мока в тестах, где JWT должен пройти
TEST_JWT_SECRET_CONFIG = [_make_secret_config(_test_private_key)]

# Неправильный PublicKey (от другой пары) — для теста с невалидной подписью
TEST_JWT_SECRET_CONFIG_WRONG = [_make_secret_config(_test_wrong_private_key)]


def get_token(username: str) -> str:
    TEST_NOT_SERVICE_USER_MAPPING["uname"] = username

    return jwt.encode(
        TEST_NOT_SERVICE_USER_MAPPING,
        key=_test_private_key,
        algorithm="RS256",
        headers={"kid": "TWork", "typ": "JWT"},
    )


class UserPayloadFactory(factory.Factory):
    """Фабрика для генерации UserCreate схем."""

    class Meta:
        model = UserCreate

    username = factory.Sequence(lambda n: f"test_user_{n}")
    access_token = factory.LazyAttribute(lambda obj: get_token(obj.username))
    access_token_expires_at = datetime.now(tz=timezone.utc) + timedelta(hours=6)
    is_superuser = False
    is_service_user = False
    ad_login = factory.Sequence(lambda n: f"test_ad_login_{n}")
    email = factory.Faker("email")
    master_id = factory.Faker("pyint", min_value=0, max_value=10000000)


class UserFactory(UserPayloadFactory, BaseSQLAlchemyModelFactory):
    """Фабрика для создания User ORM объектов."""

    class Meta(BaseMeta):
        model = User
