"""Тесты создания объектов nutrition домена."""

from http import HTTPStatus

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel
from pytest_lazy_fixtures import lf as lazy_fixture

from nutrition_tracking_api.orm.choices.history import HistoryActionEnum
from nutrition_tracking_api.orm.models import Base, User
from nutrition_tracking_api.orm.models.nutrition import FoodItem, MealEntry, MealFoodItem, NutritionGoal, WeightLog


@pytest.mark.parametrize(
    ("path", "model_data"),
    [
        ("/foods/", lazy_fixture("food_item_payload")),
        ("/meal-items/", lazy_fixture("meal_food_item_payload")),
        ("/meals/", lazy_fixture("meal_entry_payload")),
        ("/goals/", lazy_fixture("nutrition_goal_payload")),
        ("/weight-logs/", lazy_fixture("weight_log_payload")),
    ],
)
def test_create_simple(client: TestClient, path: str, model_data: BaseModel) -> None:
    result = client.post(path, content=model_data.model_dump_json())
    assert result.status_code == HTTPStatus.CREATED, result.json()
    assert result.json()["id"]


@pytest.mark.parametrize(
    ("path", "model_data"),
    [
        ("/foods/", lazy_fixture("food_item_payload")),
    ],
)
def test_create_history(client: TestClient, path: str, model_data: BaseModel) -> None:
    result = client.post(path, content=model_data.model_dump_json())

    history_records = client.get("/core/history/").json()["items"]
    assert len(history_records) == 1
    assert history_records[0]["action"] == HistoryActionEnum.CREATE
    assert history_records[0]["object_id"] == result.json()["id"]


@pytest.mark.parametrize(
    ("path", "model_data", "model_class"),
    [
        ("/foods/", lazy_fixture("food_item_payload"), FoodItem),
        ("/meal-items/", lazy_fixture("meal_food_item_payload"), MealFoodItem),
        ("/meals/", lazy_fixture("meal_entry_payload"), MealEntry),
        ("/goals/", lazy_fixture("nutrition_goal_payload"), NutritionGoal),
        ("/weight-logs/", lazy_fixture("weight_log_payload"), WeightLog),
    ],
)
def test_create_add_actions_author(
    client: TestClient, path: str, model_data: BaseModel, model_class: Base, superuser: User
) -> None:
    result = client.post(
        path,
        content=model_data.model_dump_json(),
        headers={"Authorization": f"Bearer {superuser.access_token}"},  # type: ignore[attr-defined]
    )
    assert result.status_code == HTTPStatus.CREATED
    if model_class.add_actions_author:
        assert result.json()["creator"]["id"] == str(superuser.id)
        assert result.json()["modifier"]["id"] == str(superuser.id)
    else:
        assert result.json().get("creator") is None
        assert result.json().get("modifier") is None
