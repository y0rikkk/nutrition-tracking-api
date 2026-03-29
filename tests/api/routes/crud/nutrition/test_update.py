"""Тесты обновления FoodItem."""

from http import HTTPStatus

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel
from pytest_lazy_fixtures import lf as lazy_fixture

from nutrition_tracking_api.api.schemas.nutrition.food_item import FoodItemUpdate
from nutrition_tracking_api.orm.choices.history import HistoryActionEnum
from nutrition_tracking_api.orm.models import Base
from nutrition_tracking_api.orm.models.auth import User


@pytest.mark.parametrize(
    ("path", "model_object", "data"),
    [
        (
            "/foods/",
            lazy_fixture("food_item"),
            FoodItemUpdate(name="updated_food"),
        ),
    ],
)
def test_update_success(
    client: TestClient,
    path: str,
    model_object: Base,
    data: BaseModel,
) -> None:
    resp = client.patch(f"{path}{model_object.id}", json=data.model_dump(exclude_unset=True))
    updated_object = client.get(f"{path}{model_object.id}")
    assert updated_object.json() == resp.json()
    assert resp.status_code == HTTPStatus.OK
    assert resp.json()["id"] == str(model_object.id)


@pytest.mark.parametrize(
    ("path", "model_object", "data"),
    [
        (
            "/foods/",
            lazy_fixture("food_item"),
            FoodItemUpdate(name="updated_food"),
        ),
    ],
)
def test_update_add_actions_author(
    client: TestClient, path: str, model_object: Base, data: BaseModel, superuser: User
) -> None:
    resp = client.patch(
        f"{path}{model_object.id}",
        json=data.model_dump(exclude_unset=True),
        headers={"Authorization": f"Bearer {superuser.access_token}"},
    )
    assert resp.status_code == HTTPStatus.OK
    if model_object.add_actions_author:
        assert resp.json()["creator"] is None
        assert resp.json()["modifier"]["id"] == str(superuser.id)
    else:
        assert "creator" not in resp.json()
        assert "modifier" not in resp.json()


@pytest.mark.parametrize(
    ("path", "model_object", "data"),
    [
        (
            "/foods/",
            lazy_fixture("food_item"),
            FoodItemUpdate(name="updated_food"),
        ),
    ],
)
def test_update_history(
    client: TestClient,
    path: str,
    model_object: Base,
    data: BaseModel,
) -> None:
    client.patch(f"{path}{model_object.id}", json=data.model_dump(exclude_unset=True))

    history_records = client.get("/core/history/").json()["items"]
    assert len(history_records) == 1
    assert history_records[0]["action"] == HistoryActionEnum.UPDATE
    assert history_records[0]["object_id"] == str(model_object.id)
