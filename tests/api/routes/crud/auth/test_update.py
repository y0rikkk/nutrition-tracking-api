"""Tests for update operations in auth domain."""

from http import HTTPStatus

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel
from pytest_lazy_fixtures import lf as lazy_fixture

from nutrition_tracking_api.api.schemas.auth.policies import PolicyUpdate
from nutrition_tracking_api.api.schemas.auth.roles import RoleUpdate
from nutrition_tracking_api.api.schemas.auth.user import UserUpdate
from nutrition_tracking_api.orm.choices.history import HistoryActionEnum
from nutrition_tracking_api.orm.models.auth import User
from nutrition_tracking_api.orm.models.base import Base


@pytest.mark.parametrize(
    ("path", "model_object", "data"),
    [
        ("/auth/users/", lazy_fixture("user"), UserUpdate(email="updated@example.com")),
        ("/auth/roles/", lazy_fixture("role"), RoleUpdate(name="updated_role")),
        ("/auth/policies/", lazy_fixture("policy"), PolicyUpdate(name="updated_policy")),
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
        ("/auth/users/", lazy_fixture("user"), UserUpdate(email="updated@example.com")),
        ("/auth/roles/", lazy_fixture("role"), RoleUpdate(name="updated_role")),
        ("/auth/policies/", lazy_fixture("policy"), PolicyUpdate(name="updated_policy")),
    ],
)
def test_update_add_actions_author(
    client: TestClient, path: str, model_object: Base, data: BaseModel, superuser: User
) -> None:
    resp = client.patch(
        f"{path}{model_object.id}",
        json=data.model_dump(exclude_unset=True),
        headers={"Authorization": f"Bearer {superuser.access_token}"},  # type: ignore[attr-defined]
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
        ("/auth/users/", lazy_fixture("user"), UserUpdate(email="updated@example.com")),
        ("/auth/roles/", lazy_fixture("role"), RoleUpdate(name="updated_role")),
        ("/auth/policies/", lazy_fixture("policy"), PolicyUpdate(name="updated_policy")),
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
