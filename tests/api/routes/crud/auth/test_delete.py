"""Tests for delete operations in auth domain."""

from http import HTTPStatus

import pytest
from fastapi.testclient import TestClient
from pytest_lazy_fixtures import lf as lazy_fixture

from nutrition_tracking_api.orm.choices.history import HistoryActionEnum
from nutrition_tracking_api.orm.models.base import Base


@pytest.mark.parametrize(
    ("path", "model_object"),
    [
        ("/auth/users/", lazy_fixture("user")),
        ("/auth/roles/", lazy_fixture("role")),
        ("/auth/policies/", lazy_fixture("policy")),
    ],
)
def test_delete(client: TestClient, path: str, model_object: Base) -> None:
    resp_ok = client.delete(f"{path}{model_object.id}")
    resp_deleted = client.get(f"{path}{model_object.id}")

    if hasattr(model_object, "is_archive"):
        assert resp_deleted.status_code == HTTPStatus.OK
        assert resp_deleted.json()["is_archive"] is True
    else:
        assert resp_ok.status_code == HTTPStatus.OK
        assert resp_deleted.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.parametrize(
    ("path", "model_object"),
    [
        ("/auth/users/", lazy_fixture("user")),
        ("/auth/roles/", lazy_fixture("role")),
        ("/auth/policies/", lazy_fixture("policy")),
    ],
)
def test_delete_history(client: TestClient, path: str, model_object: Base) -> None:
    client.delete(f"{path}{model_object.id}")

    history_records = client.get("/core/history/").json()["items"]
    assert len(history_records) == 1

    if hasattr(model_object, "is_archive"):
        assert history_records[0]["action"] == HistoryActionEnum.ARCHIVE

        resp_recover = client.patch(f"{path}{model_object.id}", json={"is_archive": False})
        assert resp_recover.status_code == HTTPStatus.OK

        history_records = client.get("/core/history/").json()["items"]
        assert len(history_records) == 2
        actions = {r["action"] for r in history_records}
        assert HistoryActionEnum.ARCHIVE in actions
        assert HistoryActionEnum.RECOVER in actions
    else:
        assert history_records[0]["action"] == HistoryActionEnum.DELETE
        assert history_records[0]["object_id"] == str(model_object.id)
