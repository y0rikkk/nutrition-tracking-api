"""Tests for get operations in auth domain."""

from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient
from pytest_lazy_fixtures import lf as lazy_fixture

from nutrition_tracking_api.api.services.auth.role import RoleService
from nutrition_tracking_api.api.services.auth.users import UserService
from nutrition_tracking_api.orm.models.base import Base
from tests.factories.auth.policy import PolicyFactory
from tests.factories.auth.role import RoleFactory
from tests.factories.auth.user import UserFactory

if TYPE_CHECKING:
    from nutrition_tracking_api.orm.models.auth import Policy, Role, User


@pytest.mark.parametrize(
    ("path", "model_object"),
    [
        ("/auth/users/", lazy_fixture("user")),
        ("/auth/roles/", lazy_fixture("role")),
        ("/auth/policies/", lazy_fixture("policy")),
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
        ("/auth/roles/", lazy_fixture("role")),
        ("/auth/policies/", lazy_fixture("policy")),
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


def test_get_multi_users(client: TestClient, user: "User") -> None:
    """/auth/users/ всегда содержит минимум сессионного суперпользователя из client-фикстуры."""
    resp = client.get("/auth/users/", params={"is_superuser": "false"})
    items = resp.json()["items"]

    assert resp.status_code == HTTPStatus.OK
    assert resp.json()["count"] == len(items) == 1
    assert items[0]["id"] == str(user.id)


@pytest.mark.parametrize(
    "path",
    [
        "/auth/roles/",
        "/auth/policies/",
    ],
)
def test_get_multi_empty(client: TestClient, path: str) -> None:
    resp = client.get(path)

    assert resp.status_code == HTTPStatus.OK
    assert resp.json()["items"] == []
    assert resp.json()["count"] == 0


def test_get_multi_empty_users(client: TestClient) -> None:
    """/auth/users/ без обычных пользователей содержит только сессионного суперпользователя."""
    resp = client.get("/auth/users/", params={"is_superuser": "false"})

    assert resp.status_code == HTTPStatus.OK
    assert resp.json()["items"] == []
    assert resp.json()["count"] == 0


def test_get_users_by_filters(
    client: TestClient,
    test_user_service: UserService,
) -> None:
    """Тест фильтрации пользователей по email, username и роли."""
    user_1: User = UserFactory(email="alice@example.com", username="alice")  # type: ignore[assignment]
    user_2: User = UserFactory(email="bob@example.com", username="bob_user")  # type: ignore[assignment]
    role: Role = RoleFactory(name="admin_role")  # type: ignore[assignment]
    test_user_service.add_roles(user_id=user_1.id, role_ids=[role.id])

    # Фильтруем по is_superuser=False чтобы исключить сессионного суперпользователя клиента
    resp_all = client.get("/auth/users/", params={"is_superuser": "false"}).json()
    assert resp_all["count"] == 2

    resp_email = client.get("/auth/users/", params={"email__ilike": "alice"}).json()
    assert resp_email["count"] == 1
    assert resp_email["items"][0]["id"] == str(user_1.id)

    resp_username = client.get("/auth/users/", params={"username__ilike": "bob"}).json()
    assert resp_username["count"] == 1
    assert resp_username["items"][0]["id"] == str(user_2.id)

    resp_role_id = client.get("/auth/users/", params={"role_id": str(role.id)}).json()
    assert resp_role_id["count"] == 1
    assert resp_role_id["items"][0]["id"] == str(user_1.id)

    resp_role_name = client.get("/auth/users/", params={"role_name__ilike": "admin"}).json()
    assert resp_role_name["count"] == 1
    assert resp_role_name["items"][0]["id"] == str(user_1.id)


def test_get_roles_by_filters(client: TestClient, test_role_service: RoleService) -> None:
    """Тест фильтрации ролей по name, is_default и policy_id."""
    role_1: Role = RoleFactory(name="admin_role", is_default=False)  # type: ignore[assignment]
    role_2: Role = RoleFactory(name="manager_role", is_default=True)  # type: ignore[assignment]
    policy_obj: Policy = PolicyFactory()  # type: ignore[assignment]
    test_role_service.add_policy(role_id=role_1.id, policy_id=policy_obj.id)

    resp_all = client.get("/auth/roles/").json()
    assert resp_all["count"] == 2

    resp_name = client.get("/auth/roles/", params={"name__ilike": "admin"}).json()
    assert resp_name["count"] == 1
    assert resp_name["items"][0]["id"] == str(role_1.id)

    resp_default = client.get("/auth/roles/", params={"is_default": True}).json()
    assert resp_default["count"] == 1
    assert resp_default["items"][0]["id"] == str(role_2.id)

    resp_policy = client.get("/auth/roles/", params={"policy_id": str(policy_obj.id)}).json()
    assert resp_policy["count"] == 1
    assert resp_policy["items"][0]["id"] == str(role_1.id)


def test_get_policies_by_filters(client: TestClient) -> None:
    """Тест фильтрации политик по name, target и action."""
    policy_1 = PolicyFactory(name="users_policy", targets=["/auth/users/"], actions=["GET"])
    policy_2 = PolicyFactory(name="roles_policy", targets=["/auth/roles/"], actions=["POST"])

    resp_all = client.get("/auth/policies/").json()
    assert resp_all["count"] == 2

    resp_name = client.get("/auth/policies/", params={"name__ilike": "users"}).json()
    assert resp_name["count"] == 1
    assert resp_name["items"][0]["id"] == str(policy_1.id)

    resp_target = client.get("/auth/policies/", params={"target__ilike": "/auth/roles/"}).json()
    assert resp_target["count"] == 1
    assert resp_target["items"][0]["id"] == str(policy_2.id)

    resp_action = client.get("/auth/policies/", params={"action__ilike": "POST"}).json()
    assert resp_action["count"] == 1
    assert resp_action["items"][0]["id"] == str(policy_2.id)
