"""Тесты получения объектов nutrition домена."""

from http import HTTPStatus

import pytest
from fastapi.testclient import TestClient
from pytest_lazy_fixtures import lf as lazy_fixture

from nutrition_tracking_api.orm.models import Base


@pytest.mark.parametrize(
    ("path", "model_object"),
    [
        ("/foods/", lazy_fixture("food_item")),
        ("/meals/", lazy_fixture("meal_entry")),
        ("/meal-items/", lazy_fixture("meal_food_item")),
        ("/goals/", lazy_fixture("nutrition_goal")),
    ],
)
def test_get(client: TestClient, path: str, model_object: Base) -> None:
    resp = client.get(f"{path}{model_object.id}")
    assert resp.status_code == HTTPStatus.OK
    assert resp.json()["id"] == str(model_object.id)
    if model_object.add_actions_author:
        assert "creator" in resp.json()
        assert "modifier" in resp.json()
    else:
        assert "creator" not in resp.json()
        assert "modifier" not in resp.json()


@pytest.mark.parametrize(
    ("path", "model_object"),
    [
        ("/foods/", lazy_fixture("food_item")),
        ("/meals/", lazy_fixture("meal_entry")),
        ("/meal-items/", lazy_fixture("meal_food_item")),
        ("/goals/", lazy_fixture("nutrition_goal")),
    ],
)
def test_get_multi(client: TestClient, path: str, model_object: Base) -> None:
    resp = client.get(path)
    items = resp.json()["items"]
    assert resp.status_code == HTTPStatus.OK
    assert resp.json()["count"] == len(items) == 1
    assert items[0]["id"] == str(model_object.id)
    if model_object.add_actions_author:
        assert "creator" in items[0]
        assert "modifier" in items[0]
    else:
        assert "creator" not in items[0]
        assert "modifier" not in items[0]


@pytest.mark.parametrize(
    "path",
    ["/foods/", "/meals/", "/meal-items/", "/goals/"],
)
def test_get_multi_empty(client: TestClient, path: str) -> None:
    resp = client.get(path)
    assert resp.status_code == HTTPStatus.OK
    assert resp.json()["items"] == []
    assert resp.json()["count"] == 0
