"""Integration tests for authentication and authorization."""

import uuid
from datetime import datetime, timedelta, timezone
from http import HTTPStatus
from typing import Any

from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from nutrition_tracking_api.api.schemas.auth.user import UserOut
from nutrition_tracking_api.api.services.auth.role import RoleService
from nutrition_tracking_api.orm.choices.history import HistoryActionEnum
from nutrition_tracking_api.orm.models.auth import Policy, Role, User
from tests.factories.auth.policy import PolicyFactory
from tests.factories.auth.role import RoleFactory, RolePayloadFactory
from tests.factories.auth.user import (
    TEST_JWT_SECRET_CONFIG,
    TEST_JWT_SECRET_CONFIG_WRONG,
    UserFactory,
    UserPayloadFactory,
)


def test_auth_existing_user(client: TestClient, user: User) -> None:
    """Пользователь существует в БД. Токен валиден (не истёк)."""
    resp = client.get(
        "/auth/users/me/",
        headers={"Authorization": f"Bearer {user.access_token}"},
    )

    assert resp.status_code == HTTPStatus.OK
    assert resp.json()["id"] == str(user.id)


def test_auth_new_user(client: TestClient, mocker: MockerFixture) -> None:
    """Пользователь НЕ существует в БД — создаётся на лету после декодирования JWT."""
    user_payload = UserPayloadFactory(access_token="new_user_token")  # noqa: S106
    default_role = RoleFactory(is_default=True)

    mocker.patch(
        "nutrition_tracking_api.api.services.auth.authorization.AuthService.get_decoded_user_from_twork_jwt_token",
        return_value=user_payload,
    )

    resp = client.get(
        "/auth/users/me/",
        headers={"Authorization": "Bearer new_user_token"},
    )

    assert resp.status_code == HTTPStatus.OK
    user_id = resp.json()["id"]

    # Verify default role was assigned
    resp_user = client.get(f"/auth/users/{user_id}")
    assert resp_user.status_code == HTTPStatus.OK
    user_data = resp_user.json()
    assert len(user_data["roles"]) == 1
    assert user_data["roles"][0]["id"] == str(default_role.id)


def test_auth_new_user_real_decode(client: TestClient, mocker: MockerFixture) -> None:
    """Пользователь НЕ в БД — JWT декодируется реально через TEST_JWT_SECRET_CONFIG."""
    user_payload = UserPayloadFactory()
    default_role = RoleFactory(is_default=True)

    mocker.patch(
        "nutrition_tracking_api.api.services.auth.authorization.get_secret_config",
        return_value=TEST_JWT_SECRET_CONFIG,
    )

    resp = client.get(
        "/auth/users/me/",
        headers={"Authorization": f"Bearer {user_payload.access_token}"},
    )

    assert resp.status_code == HTTPStatus.OK
    user_id = resp.json()["id"]

    resp_user = client.get(f"/auth/users/{user_id}")
    assert resp_user.status_code == HTTPStatus.OK
    user_data = resp_user.json()
    assert len(user_data["roles"]) == 1
    assert user_data["roles"][0]["id"] == str(default_role.id)
    assert user_data["username"] == user_payload.username


def test_user_bad_verify(client: TestClient, mocker: MockerFixture) -> None:
    """Ключ в JWKS найден, но подпись токена невалидна (другой ключ) → 401."""
    user_payload = UserPayloadFactory()

    mocker.patch(
        "nutrition_tracking_api.api.services.auth.authorization.get_secret_config",
        return_value=TEST_JWT_SECRET_CONFIG_WRONG,
    )

    resp = client.get(
        "/auth/users/me/",
        headers={"Authorization": f"Bearer {user_payload.access_token}"},
    )

    assert resp.status_code == HTTPStatus.UNAUTHORIZED
    assert resp.json() == {"detail": "Токен для авторизации невалиден"}


def test_expired_token_authentication(client: TestClient) -> None:
    """Пользователь в БД, но токен истёк."""
    user = UserFactory(access_token_expires_at=datetime.now(tz=timezone.utc) - timedelta(hours=1))

    resp = client.get(
        "/auth/users/me/",
        headers={"Authorization": f"Bearer {user.access_token}"},
    )

    assert resp.status_code == HTTPStatus.UNAUTHORIZED
    assert resp.json() == {"detail": "Токен авторизации истек"}


def test_user_bad_permissions(client: TestClient, user_with_permissions: UserOut) -> None:
    """Пользователь с правами на /auth/users/ пытается GET /auth/roles/ → 403."""
    resp = client.get(
        "/auth/roles/",
        headers={"Authorization": f"Bearer {user_with_permissions.access_token}"},
    )

    assert resp.status_code == HTTPStatus.FORBIDDEN
    assert resp.json() == {"detail": "Вам нужно больше прав для выполнения этого действия"}


def test_user_ok_permissions(client: TestClient, user_with_permissions: UserOut) -> None:
    """Пользователь с правами на /auth/users/ успешно обращается к /auth/users/."""
    resp = client.get(
        "/auth/users/",
        headers={"Authorization": f"Bearer {user_with_permissions.access_token}"},
    )

    assert resp.status_code == HTTPStatus.OK
    assert resp.json()["count"] >= 1


def test_superuser_access(client: TestClient, superuser: User) -> None:
    """Суперпользователь не требует политик — доступ везде."""
    resp = client.get(
        "/auth/roles/",
        headers={"Authorization": f"Bearer {superuser.access_token}"},
    )

    assert resp.status_code == HTTPStatus.OK


def test_user_path_validation_with_slashes(client: TestClient, make_user_with_permissions: Any) -> None:
    """Политика с target без trailing slash матчится на путь с slash и наоборот."""
    user_out = make_user_with_permissions(
        targets=["/auth/users", "/auth/users/{object_id}"],  # без trailing slash
        actions=["GET"],
    )

    resp = client.get(
        "/auth/users/",  # с trailing slash
        headers={"Authorization": f"Bearer {user_out.access_token}"},
    )

    assert resp.status_code == HTTPStatus.OK


def test_user_ok_matcher_rule(client: TestClient, make_user_with_permissions: Any) -> None:
    """Matcher field="id" eq "$user.id" фильтрует CRUD-результаты."""
    UserFactory()  # посторонний пользователь в БД
    user_a = make_user_with_permissions(
        targets=["/auth/users/", "/auth/users/{object_id}"],
        actions=["GET"],
        matchers=[{"field": "id", "condition": "eq", "value": "$user.id"}],
    )

    resp = client.get(
        "/auth/users/",
        headers={"Authorization": f"Bearer {user_a.access_token}"},
    )

    assert resp.status_code == HTTPStatus.OK
    data = resp.json()
    assert data["count"] == 1
    assert data["items"][0]["id"] == str(user_a.id)


def test_get_me(
    client: TestClient,
    make_user_with_permissions: Any,
    test_role_service: RoleService,
) -> None:
    """GET /auth/users/me/ проверяет OR между политиками и AND внутри политики.

    Политика 1 (один matcher) и Политика 2 (два matcher) применены к одной роли
    для одного target+action. Ожидаем два entry в списке (OR), второй содержит
    оба matcher-а в одном словаре (AND).
    """
    # Политика 1: один matcher по id
    user_out: UserOut = make_user_with_permissions(
        targets=["/auth/users/"],
        actions=["GET"],
        matchers=[{"field": "id", "condition": "eq", "value": "$user.id"}],
        options=["Approve"],
    )

    # Политика 2: два matcher — AND внутри одной политики
    and_policy: Policy = PolicyFactory(  # type: ignore[assignment]
        targets=["/auth/users/"],
        actions=["GET"],
        matchers=[
            {"field": "id", "condition": "eq", "value": "$user.id"},
            {"field": "username", "condition": "eq", "value": "$user.username"},
        ],
    )
    test_role_service.add_policy(
        role_id=user_out.roles[0].id,
        policy_id=and_policy.id,
    )

    resp = client.get(
        "/auth/users/me/",
        headers={"Authorization": f"Bearer {user_out.access_token}"},
    )

    assert resp.status_code == HTTPStatus.OK
    data = resp.json()
    assert data["id"] == str(user_out.id)
    # OR: два отдельных entry — один на каждую политику
    assert sorted(data["permissions"]) == sorted(
        {
            "/auth/users/": {
                "GET": [
                    # Политика 1 — один matcher
                    {
                        "matchers": {"id": {"value": str(user_out.id), "condition": "eq"}},
                        "options": ["Approve"],
                    },
                    # Политика 2 — два matcher одновременно (AND)
                    {
                        "matchers": {
                            "id": {"value": str(user_out.id), "condition": "eq"},
                            "username": {"value": user_out.username, "condition": "eq"},
                        },
                        "options": None,
                    },
                ],
            },
        }
    )


def test_add_remove_role(client: TestClient, user: User, role: Role) -> None:
    """Полный цикл добавления/удаления роли у пользователя + ошибочные сценарии."""
    # --- Добавление роли ---
    resp = client.patch(f"/auth/users/{user.id}/add-role/{role.id}")
    assert resp.status_code == HTTPStatus.OK
    data = resp.json()
    assert any(r["id"] == str(role.id) for r in data["roles"])

    # --- Дублирование роли ---
    resp = client.patch(f"/auth/users/{user.id}/add-role/{role.id}")
    assert resp.status_code == HTTPStatus.BAD_REQUEST
    assert resp.json() == {"detail": "Ошибка. Схожий объект уже есть в базе данных"}

    # --- Несуществующая роль при добавлении ---
    nonexistent_role_id = uuid.uuid4()
    resp = client.patch(f"/auth/users/{user.id}/add-role/{nonexistent_role_id}")
    assert resp.status_code == HTTPStatus.BAD_REQUEST
    assert resp.json() == {"detail": "Ошибка внешнего ключа"}

    # --- Удаление несуществующей роли ---
    resp = client.delete(f"/auth/users/{user.id}/remove-role/{nonexistent_role_id}")
    assert resp.status_code == HTTPStatus.NOT_FOUND
    assert resp.json() == {"detail": "Объект не найден в базе данных или недостаточно прав для выполнения операции"}

    # --- Удаление роли ---
    resp = client.delete(f"/auth/users/{user.id}/remove-role/{role.id}")
    assert resp.status_code == HTTPStatus.OK
    data = resp.json()
    assert data["roles"] == []


def test_add_remove_policy(client: TestClient, role: Role, policy: Policy) -> None:
    """Полный цикл добавления/удаления политики у роли + ошибочные сценарии."""
    # --- Добавление политики ---
    resp = client.patch(f"/auth/roles/{role.id}/add-policy/{policy.id}")
    assert resp.status_code == HTTPStatus.OK
    data = resp.json()
    assert any(p["id"] == str(policy.id) for p in data["policies"])

    # --- Дублирование политики ---
    resp = client.patch(f"/auth/roles/{role.id}/add-policy/{policy.id}")
    assert resp.status_code == HTTPStatus.BAD_REQUEST
    assert resp.json() == {"detail": "Ошибка. Схожий объект уже есть в базе данных"}

    # --- Несуществующая политика при добавлении ---
    nonexistent_policy_id = uuid.uuid4()
    resp = client.patch(f"/auth/roles/{role.id}/add-policy/{nonexistent_policy_id}")
    assert resp.status_code == HTTPStatus.BAD_REQUEST
    assert resp.json() == {"detail": "Ошибка внешнего ключа"}

    # --- Удаление несуществующей политики ---
    resp = client.delete(f"/auth/roles/{role.id}/remove-policy/{nonexistent_policy_id}")
    assert resp.status_code == HTTPStatus.NOT_FOUND
    assert resp.json() == {"detail": "Объект не найден в базе данных или недостаточно прав для выполнения операции"}

    # --- Удаление политики ---
    resp = client.delete(f"/auth/roles/{role.id}/remove-policy/{policy.id}")
    assert resp.status_code == HTTPStatus.OK
    data = resp.json()
    assert data["policies"] == []


def test_user_roles_history(client: TestClient, user: User, role: Role) -> None:
    """add_roles и remove_roles создают записи истории с action=update и корректным diff_obj."""
    # === add_roles: добавляем роль пользователю ===
    resp_add = client.patch(f"/auth/users/{user.id}/add-role/{role.id}")
    assert resp_add.status_code == HTTPStatus.OK

    history = client.get("/core/history/").json()["items"]
    assert len(history) == 1

    add_record = history[0]
    assert add_record["action"] == HistoryActionEnum.UPDATE
    assert add_record["object_id"] == str(user.id)
    assert add_record["parent_id"] == str(user.id)
    assert add_record["parent_type"] == "User"
    # Единственное изменение — role_ids: [] → [role.id]
    assert add_record["payload"]["diff_obj"] == {"role_ids": [str(role.id)]}

    # === remove_roles: убираем роль у пользователя ===
    resp_remove = client.delete(f"/auth/users/{user.id}/remove-role/{role.id}")
    assert resp_remove.status_code == HTTPStatus.OK

    history = client.get("/core/history/").json()["items"]
    assert len(history) == 2

    # Находим запись об удалении по пустому role_ids в diff_obj
    remove_record = next(r for r in history if r["payload"]["diff_obj"].get("role_ids") == [])
    assert remove_record["action"] == HistoryActionEnum.UPDATE
    assert remove_record["object_id"] == str(user.id)
    assert remove_record["parent_id"] == str(user.id)
    assert remove_record["parent_type"] == "User"
    # role_ids: [role.id] → []
    assert remove_record["payload"]["diff_obj"] == {"role_ids": []}


def test_role_policies_history(client: TestClient, role: Role, policy: Policy) -> None:
    """add_policy и remove_policy создают записи истории с action=update и корректным diff_obj."""
    # === add_policy: добавляем политику к роли ===
    resp_add = client.patch(f"/auth/roles/{role.id}/add-policy/{policy.id}")
    assert resp_add.status_code == HTTPStatus.OK

    history = client.get("/core/history/").json()["items"]
    assert len(history) == 1

    add_record = history[0]
    assert add_record["action"] == HistoryActionEnum.UPDATE
    assert add_record["object_id"] == str(role.id)
    assert add_record["parent_id"] == str(role.id)
    assert add_record["parent_type"] == "Role"
    # Единственное изменение — policy_ids: [] → [policy.id]
    assert add_record["payload"]["diff_obj"] == {"policy_ids": [str(policy.id)]}

    # === remove_policy: убираем политику у роли ===
    resp_remove = client.delete(f"/auth/roles/{role.id}/remove-policy/{policy.id}")
    assert resp_remove.status_code == HTTPStatus.OK

    history = client.get("/core/history/").json()["items"]
    assert len(history) == 2

    # Находим запись об удалении по пустому policy_ids в diff_obj
    remove_record = next(r for r in history if r["payload"]["diff_obj"].get("policy_ids") == [])
    assert remove_record["action"] == HistoryActionEnum.UPDATE
    assert remove_record["object_id"] == str(role.id)
    assert remove_record["parent_id"] == str(role.id)
    assert remove_record["parent_type"] == "Role"
    # policy_ids: [policy.id] → []
    assert remove_record["payload"]["diff_obj"] == {"policy_ids": []}


def test_create_role(client: TestClient) -> None:
    role_1 = RolePayloadFactory(is_default=True)
    role_2 = RolePayloadFactory(is_default=True)
    role_3 = RolePayloadFactory(is_default=False)

    resp_create_role = client.post("/auth/roles/", json=role_1.model_dump())  # type: ignore[attr-defined]
    resp_error = client.post("/auth/roles/", json=role_2.model_dump())  # type: ignore[attr-defined]
    role_2.is_default = False
    resp_ok = client.post("/auth/roles/", json=role_2.model_dump())  # type: ignore[attr-defined]
    resp_create_role_3 = client.post("/auth/roles/", json=role_3.model_dump())  # type: ignore[attr-defined]

    assert resp_create_role.status_code == HTTPStatus.CREATED
    assert resp_error.status_code == HTTPStatus.BAD_REQUEST
    assert resp_ok.status_code == HTTPStatus.CREATED
    assert resp_create_role_3.status_code == HTTPStatus.CREATED
