"""Fixtures for CRUD route tests."""

import pytest

from nutrition_tracking_api.api.schemas.auth.policies import PolicyCreate
from nutrition_tracking_api.api.schemas.auth.roles import RoleCreate
from nutrition_tracking_api.api.schemas.auth.user import UserCreate
from nutrition_tracking_api.api.schemas.nutrition.food_item import FoodItemCreate
from tests.factories.auth.policy import PolicyPayloadFactory
from tests.factories.auth.role import RolePayloadFactory
from tests.factories.auth.user import UserPayloadFactory
from tests.factories.nutrition.food_item import FoodItemPayloadFactory


@pytest.fixture
def user_payload() -> UserCreate:
    """Payload fixture для создания User."""
    return UserPayloadFactory()  # type: ignore[return-value]


@pytest.fixture
def role_payload() -> RoleCreate:
    """Payload fixture для создания Role."""
    return RolePayloadFactory()  # type: ignore[return-value]


@pytest.fixture
def policy_payload() -> PolicyCreate:
    """Payload fixture для создания Policy."""
    return PolicyPayloadFactory()  # type: ignore[return-value]


@pytest.fixture
def food_item_payload() -> FoodItemCreate:
    """Payload fixture для создания FoodItem."""
    return FoodItemPayloadFactory()  # type: ignore[return-value]
