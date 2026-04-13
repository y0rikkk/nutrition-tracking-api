"""Тесты Dashboard endpoint."""

import datetime
from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient

from tests.factories.nutrition.meal_entry import MealEntryFactory
from tests.factories.nutrition.meal_food_item import MealFoodItemFactory
from tests.factories.nutrition.nutrition_goal import NutritionGoalFactory

if TYPE_CHECKING:
    from nutrition_tracking_api.orm.models.auth import User

TODAY = datetime.datetime.now().date()
YESTERDAY = TODAY - datetime.timedelta(days=1)

_AUTH = pytest.fixture  # просто alias для читаемости


# ---------------------------------------------------------------------------
# Вспомогательная функция
# ---------------------------------------------------------------------------


def _headers(user: "User") -> dict[str, str]:
    return {"Authorization": f"Bearer {user.access_token}"}  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Базовые тесты
# ---------------------------------------------------------------------------


def test_dashboard_empty_day(client: TestClient, nutrition_user: "User") -> None:
    """Нет приёмов пищи за день → consumed нули, пустые списки."""
    resp = client.get("/dashboard/", params={"date": str(TODAY)}, headers=_headers(nutrition_user))

    assert resp.status_code == HTTPStatus.OK
    data = resp.json()
    assert data["date"] == str(TODAY)
    assert data["consumed"]["calories_kcal"] == 0
    assert data["consumed"]["protein_g"] == 0
    assert data["consumed"]["fat_g"] == 0
    assert data["consumed"]["carbs_g"] == 0
    assert data["meals"] == []
    assert data["meal_breakdown"] == []
    assert data["goal"] is None
    assert data["goal_progress"] is None


def test_dashboard_with_meals(client: TestClient, nutrition_user: "User") -> None:
    """Приёмы с составом → consumed равен сумме КБЖУ всех items."""
    meal = MealEntryFactory(user=nutrition_user, date=TODAY)
    item1 = MealFoodItemFactory(meal_entry=meal, calories_kcal=300.0, protein_g=20.0, fat_g=10.0, carbs_g=40.0)
    item2 = MealFoodItemFactory(meal_entry=meal, calories_kcal=200.0, protein_g=15.0, fat_g=8.0, carbs_g=25.0)

    resp = client.get("/dashboard/", params={"date": str(TODAY)}, headers=_headers(nutrition_user))

    assert resp.status_code == HTTPStatus.OK
    data = resp.json()
    assert data["consumed"]["calories_kcal"] == item1.calories_kcal + item2.calories_kcal
    assert data["consumed"]["protein_g"] == item1.protein_g + item2.protein_g
    assert data["consumed"]["fat_g"] == item1.fat_g + item2.fat_g
    assert data["consumed"]["carbs_g"] == item1.carbs_g + item2.carbs_g
    assert len(data["meals"]) == 1
    assert len(data["meals"][0]["items"]) == 2


# ---------------------------------------------------------------------------
# Цели и прогресс
# ---------------------------------------------------------------------------


def test_dashboard_with_active_goal(client: TestClient, nutrition_user: "User") -> None:
    """Есть активная цель → goal_progress заполнен."""
    NutritionGoalFactory(
        user=nutrition_user,
        is_active=True,
        calories_kcal=2000.0,
        protein_g=100.0,
        fat_g=70.0,
        carbs_g=250.0,
    )
    meal = MealEntryFactory(user=nutrition_user, date=TODAY)
    MealFoodItemFactory(meal_entry=meal, calories_kcal=1000.0, protein_g=50.0, fat_g=35.0, carbs_g=125.0)

    resp = client.get("/dashboard/", params={"date": str(TODAY)}, headers=_headers(nutrition_user))

    assert resp.status_code == HTTPStatus.OK
    data = resp.json()
    assert data["goal"] is not None
    assert data["goal_progress"] is not None
    assert data["goal_progress"]["calories"]["consumed"] == 1000.0
    assert data["goal_progress"]["calories"]["goal"] == 2000.0
    assert data["goal_progress"]["calories"]["remaining"] == 1000.0
    assert data["goal_progress"]["calories"]["percent"] == 50.0


def test_dashboard_no_active_goal(client: TestClient, nutrition_user: "User") -> None:
    """Нет активной цели → goal и goal_progress равны None."""
    resp = client.get("/dashboard/", params={"date": str(TODAY)}, headers=_headers(nutrition_user))

    assert resp.status_code == HTTPStatus.OK
    data = resp.json()
    assert data["goal"] is None
    assert data["goal_progress"] is None


def test_dashboard_goal_progress_over_100(client: TestClient, nutrition_user: "User") -> None:
    """Consumed > goal → remaining отрицательный, percent > 100."""
    NutritionGoalFactory(
        user=nutrition_user, is_active=True, calories_kcal=1000.0, protein_g=50.0, fat_g=30.0, carbs_g=100.0
    )
    meal = MealEntryFactory(user=nutrition_user, date=TODAY)
    MealFoodItemFactory(meal_entry=meal, calories_kcal=1500.0, protein_g=70.0, fat_g=50.0, carbs_g=150.0)

    resp = client.get("/dashboard/", params={"date": str(TODAY)}, headers=_headers(nutrition_user))

    data = resp.json()
    assert data["goal_progress"]["calories"]["remaining"] == -500.0
    assert data["goal_progress"]["calories"]["percent"] == 150.0


# ---------------------------------------------------------------------------
# Вес
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Фильтрация по дате
# ---------------------------------------------------------------------------


def test_dashboard_date_filter(client: TestClient, nutrition_user: "User") -> None:
    """Приёмы за разные даты → запрос за конкретную дату возвращает только её приёмы."""
    MealEntryFactory(user=nutrition_user, date=TODAY)
    MealEntryFactory(user=nutrition_user, date=YESTERDAY)

    resp_today = client.get("/dashboard/", params={"date": str(TODAY)}, headers=_headers(nutrition_user))
    resp_yesterday = client.get("/dashboard/", params={"date": str(YESTERDAY)}, headers=_headers(nutrition_user))

    assert len(resp_today.json()["meals"]) == 1
    assert resp_today.json()["meals"][0]["date"] == str(TODAY)
    assert len(resp_yesterday.json()["meals"]) == 1
    assert resp_yesterday.json()["meals"][0]["date"] == str(YESTERDAY)


def test_dashboard_default_date_is_today(client: TestClient, nutrition_user: "User") -> None:
    """Без параметра date → используется сегодняшняя дата."""
    MealEntryFactory(user=nutrition_user, date=TODAY)
    MealEntryFactory(user=nutrition_user, date=YESTERDAY)

    resp = client.get("/dashboard/", headers=_headers(nutrition_user))

    assert resp.status_code == HTTPStatus.OK
    assert resp.json()["date"] == str(TODAY)
    assert len(resp.json()["meals"]) == 1


# ---------------------------------------------------------------------------
# Разбивка по типам приёма пищи
# ---------------------------------------------------------------------------


def test_dashboard_meal_breakdown(client: TestClient, nutrition_user: "User") -> None:
    """Завтрак + ужин → 2 записи в meal_breakdown, суммы верные."""
    from nutrition_tracking_api.api.schemas.nutrition.meal_entry import MealTypeEnum

    breakfast = MealEntryFactory(user=nutrition_user, date=TODAY, meal_type=MealTypeEnum.breakfast)
    MealFoodItemFactory(meal_entry=breakfast, calories_kcal=400.0, protein_g=20.0, fat_g=15.0, carbs_g=50.0)

    dinner = MealEntryFactory(user=nutrition_user, date=TODAY, meal_type=MealTypeEnum.dinner)
    MealFoodItemFactory(meal_entry=dinner, calories_kcal=600.0, protein_g=35.0, fat_g=20.0, carbs_g=80.0)

    resp = client.get("/dashboard/", params={"date": str(TODAY)}, headers=_headers(nutrition_user))

    data = resp.json()
    breakdown = {b["meal_type"]: b["totals"] for b in data["meal_breakdown"]}

    assert set(breakdown.keys()) == {"breakfast", "dinner"}
    assert breakdown["breakfast"]["calories_kcal"] == 400.0
    assert breakdown["dinner"]["calories_kcal"] == 600.0


def test_dashboard_meal_breakdown_order(client: TestClient, nutrition_user: "User") -> None:
    """Порядок в breakdown: breakfast → lunch → dinner → snack."""
    from nutrition_tracking_api.api.schemas.nutrition.meal_entry import MealTypeEnum

    MealEntryFactory(user=nutrition_user, date=TODAY, meal_type=MealTypeEnum.snack)
    MealEntryFactory(user=nutrition_user, date=TODAY, meal_type=MealTypeEnum.breakfast)
    MealEntryFactory(user=nutrition_user, date=TODAY, meal_type=MealTypeEnum.dinner)

    resp = client.get("/dashboard/", params={"date": str(TODAY)}, headers=_headers(nutrition_user))
    types = [b["meal_type"] for b in resp.json()["meal_breakdown"]]

    assert types == ["breakfast", "dinner", "snack"]


# ---------------------------------------------------------------------------
# Авторизация и изоляция
# ---------------------------------------------------------------------------


def test_dashboard_requires_auth() -> None:
    """Без заголовка Authorization → 401/403."""
    from nutrition_tracking_api.api.main import app

    with TestClient(app) as c:
        resp = c.get("/dashboard/")
    assert resp.status_code in (HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN)


def test_dashboard_user_isolation(client: TestClient, nutrition_user: "User") -> None:
    """Каждый пользователь видит только свои данные."""
    from tests.factories.auth.user import UserFactory

    other_user = UserFactory()
    MealEntryFactory(user=other_user, date=TODAY)
    MealEntryFactory(user=nutrition_user, date=TODAY)

    resp = client.get("/dashboard/", params={"date": str(TODAY)}, headers=_headers(nutrition_user))

    assert resp.status_code == HTTPStatus.OK
    assert len(resp.json()["meals"]) == 1
