"""Тесты удаления объектов nutrition домена."""

from http import HTTPStatus

import pytest
from fastapi.testclient import TestClient
from pytest_lazy_fixtures import lf as lazy_fixture

from nutrition_tracking_api.orm.choices.history import HistoryActionEnum
from nutrition_tracking_api.orm.models import Base


@pytest.mark.parametrize(
    ("path", "model_object"),
    [
        ("/foods/", lazy_fixture("food_item")),
        ("/meals/", lazy_fixture("meal_entry")),
        ("/meal-items/", lazy_fixture("meal_food_item")),
    ],
)
def test_delete(client: TestClient, path: str, model_object: Base) -> None:
    resp_ok = client.delete(f"{path}{model_object.id}")
    resp_deleted = client.get(f"{path}{model_object.id}")

    if hasattr(model_object, "is_archive"):
        # Soft delete: объект остается, но помечается is_archive=True
        assert resp_ok.status_code == HTTPStatus.OK
        assert resp_deleted.status_code == HTTPStatus.OK
        assert resp_deleted.json()["is_archive"] is True
    else:
        # Hard delete: объект удаляется
        assert resp_ok.status_code == HTTPStatus.OK
        assert resp_deleted.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.parametrize(
    ("path", "model_object"),
    [
        ("/foods/", lazy_fixture("food_item")),
    ],
)
def test_delete_history(client: TestClient, path: str, model_object: Base) -> None:
    client.delete(f"{path}{model_object.id}")

    history_records = client.get("/core/history/").json()["items"]
    assert len(history_records) == 1

    if hasattr(model_object, "is_archive"):
        # Soft delete → ARCHIVE action
        assert history_records[0]["action"] == HistoryActionEnum.ARCHIVE

        resp_recover = client.patch(f"{path}{model_object.id}", json={"is_archive": False})
        assert resp_recover.status_code == HTTPStatus.OK

        history_records = client.get("/core/history/").json()["items"]
        assert len(history_records) == 2
        actions = {r["action"] for r in history_records}
        assert HistoryActionEnum.ARCHIVE in actions
        assert HistoryActionEnum.RECOVER in actions
    else:
        # Hard delete → DELETE action
        assert history_records[0]["action"] == HistoryActionEnum.DELETE
        assert history_records[0]["object_id"] == str(model_object.id)
