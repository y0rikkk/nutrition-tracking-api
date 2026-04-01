"""Fixtures for CRUD route tests."""

import pytest

from nutrition_tracking_api.api.schemas.auth.policies import PolicyCreate
from nutrition_tracking_api.api.schemas.auth.roles import RoleCreate
from nutrition_tracking_api.api.schemas.auth.user import UserCreate
from nutrition_tracking_api.api.schemas.nutrition.food_item import FoodItemCreate
from nutrition_tracking_api.api.schemas.nutrition.meal_entry import MealEntryCreate
from nutrition_tracking_api.api.schemas.nutrition.meal_food_item import MealFoodItemCreate
from nutrition_tracking_api.api.schemas.nutrition.nutrition_goal import NutritionGoalCreate
from tests.factories.auth.policy import PolicyPayloadFactory
from tests.factories.auth.role import RolePayloadFactory
from tests.factories.auth.user import UserPayloadFactory
from tests.factories.nutrition.food_item import FoodItemPayloadFactory
from tests.factories.nutrition.meal_entry import MealEntryPayloadFactory
from tests.factories.nutrition.meal_food_item import MealFoodItemPayloadFactory
from tests.factories.nutrition.nutrition_goal import NutritionGoalPayloadFactory


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


@pytest.fixture
def meal_entry_payload() -> MealEntryCreate:
    """Payload fixture для создания MealEntry."""
    return MealEntryPayloadFactory()  # type: ignore[return-value]


@pytest.fixture
def meal_food_item_payload() -> MealFoodItemCreate:
    """Payload fixture для создания MealFoodItem (ручной ввод)."""
    return MealFoodItemPayloadFactory()  # type: ignore[return-value]


@pytest.fixture
def nutrition_goal_payload() -> NutritionGoalCreate:
    """Payload fixture для создания NutritionGoal."""
    return NutritionGoalPayloadFactory()  # type: ignore[return-value]
