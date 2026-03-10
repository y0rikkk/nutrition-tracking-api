"""Tests for create operations in auth domain."""

from http import HTTPStatus

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel
from pytest_lazy_fixtures import lf as lazy_fixture

from nutrition_tracking_api.orm.choices.history import HistoryActionEnum
from nutrition_tracking_api.orm.models.auth import Policy, Role, User
from nutrition_tracking_api.orm.models.base import Base


@pytest.mark.parametrize(
    ("path", "model_data"),
    [
        ("/auth/users/", lazy_fixture("user_payload")),
        ("/auth/roles/", lazy_fixture("role_payload")),
        ("/auth/policies/", lazy_fixture("policy_payload")),
    ],
)
def test_create_simple(client: TestClient, path: str, model_data: BaseModel) -> None:
    result = client.post(
        path,
        content=model_data.model_dump_json(),
    )
    assert result.status_code == HTTPStatus.CREATED, result.json()
    assert result.json()["id"]


@pytest.mark.parametrize(
    ("path", "model_data"),
    [
        ("/auth/users/", lazy_fixture("user_payload")),
        ("/auth/roles/", lazy_fixture("role_payload")),
        ("/auth/policies/", lazy_fixture("policy_payload")),
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
        ("/auth/users/", lazy_fixture("user_payload"), User),
        ("/auth/roles/", lazy_fixture("role_payload"), Role),
        ("/auth/policies/", lazy_fixture("policy_payload"), Policy),
    ],
)
def test_create_add_actions_author(
    client: TestClient, path: str, model_data: BaseModel, model_class: Base, superuser: User
) -> None:
    result = client.post(
        path,
        content=model_data.model_dump_json(),
        headers={"Authorization": f"Bearer {superuser.access_token}"},
    )
    assert result.status_code == HTTPStatus.CREATED
    if model_class.add_actions_author:
        assert result.json()["creator"]["id"] == str(superuser.id)
        assert result.json()["modifier"]["id"] == str(superuser.id)
    else:
        assert result.json().get("creator") is None
        assert result.json().get("modifier") is None
