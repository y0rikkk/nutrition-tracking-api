"""Тесты эндпоинта POST /advice/."""

from http import HTTPStatus
from typing import TYPE_CHECKING

from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from tests.factories.nutrition.meal_entry import MealEntryFactory
from tests.factories.nutrition.meal_food_item import MealFoodItemFactory
from tests.factories.nutrition.nutrition_goal import NutritionGoalFactory
from tests.factories.nutrition.weight_log import WeightLogFactory

if TYPE_CHECKING:
    from nutrition_tracking_api.orm.models.auth import User

_MOCK_ADVICE = "Совет: ешь больше белка и пей воду."
_OPENROUTER_CHAT = "nutrition_tracking_api.integrations.openrouter.OpenRouterClient.chat"


def _headers(user: "User") -> dict[str, str]:
    return {"Authorization": f"Bearer {user.access_token}"}  # type: ignore[attr-defined]


def test_advice_returns_text(
    client: TestClient,
    nutrition_user: "User",
    mocker: MockerFixture,
) -> None:
    """Базовый запрос возвращает непустой совет."""
    mocker.patch(_OPENROUTER_CHAT, return_value=_MOCK_ADVICE)

    resp = client.post("/advice/", json={}, headers=_headers(nutrition_user))

    assert resp.status_code == HTTPStatus.OK
    assert resp.json()["advice"] == _MOCK_ADVICE


def test_advice_with_question(
    client: TestClient,
    nutrition_user: "User",
    mocker: MockerFixture,
) -> None:
    """Вопрос пользователя попадает в промпт к LLM."""
    mock_chat = mocker.patch(_OPENROUTER_CHAT, return_value=_MOCK_ADVICE)

    client.post(
        "/advice/",
        json={"question": "Стоит ли мне есть углеводы вечером?"},
        headers=_headers(nutrition_user),
    )

    call_messages = mock_chat.call_args[0][0]
    user_message = next(m["content"] for m in call_messages if m["role"] == "user")
    assert "Стоит ли мне есть углеводы вечером?" in user_message


def test_advice_without_goal(
    client: TestClient,
    nutrition_user: "User",
    mocker: MockerFixture,
) -> None:
    """Нет активной цели — сервис не падает."""
    mocker.patch(_OPENROUTER_CHAT, return_value=_MOCK_ADVICE)

    resp = client.post("/advice/", json={}, headers=_headers(nutrition_user))

    assert resp.status_code == HTTPStatus.OK
    _ = mocker.patch(_OPENROUTER_CHAT).call_args
    # Нет цели — моку было вызвано без падения
    assert resp.json()["advice"] == _MOCK_ADVICE


def test_advice_without_meals(
    client: TestClient,
    nutrition_user: "User",
    mocker: MockerFixture,
) -> None:
    """Нет приёмов пищи — сервис не падает, данные питания отмечены как отсутствующие."""
    mock_chat = mocker.patch(_OPENROUTER_CHAT, return_value=_MOCK_ADVICE)

    resp = client.post("/advice/", json={"days": 3}, headers=_headers(nutrition_user))

    assert resp.status_code == HTTPStatus.OK
    user_message = next(m["content"] for m in mock_chat.call_args[0][0] if m["role"] == "user")
    assert "данных нет" in user_message


def test_advice_with_meals_and_goal(
    client: TestClient,
    nutrition_user: "User",
    mocker: MockerFixture,
) -> None:
    """Данные питания и цель попадают в промпт к LLM."""
    mock_chat = mocker.patch(_OPENROUTER_CHAT, return_value=_MOCK_ADVICE)

    goal = NutritionGoalFactory(user=nutrition_user, calories_kcal=2000.0)
    meal = MealEntryFactory(user=nutrition_user)
    MealFoodItemFactory(meal_entry=meal, calories_kcal=500.0, protein_g=30.0, fat_g=10.0, carbs_g=60.0)
    WeightLogFactory(user=nutrition_user, weight_kg=75.0)

    resp = client.post("/advice/", json={"days": 7}, headers=_headers(nutrition_user))

    assert resp.status_code == HTTPStatus.OK
    user_message = next(m["content"] for m in mock_chat.call_args[0][0] if m["role"] == "user")
    assert "2000" in user_message  # цель по калориям в промпте
    assert "500" in user_message  # потреблённые калории в промпте
    assert "75.0" in user_message  # вес в промпте
    _ = goal  # используется через nutrition_user


def test_advice_requires_auth() -> None:
    """Без токена — 401."""
    from nutrition_tracking_api.api.main import app

    with TestClient(app) as unauthenticated_client:
        resp = unauthenticated_client.post("/advice/", json={})

    assert resp.status_code == HTTPStatus.UNAUTHORIZED
