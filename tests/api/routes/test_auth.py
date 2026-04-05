"""Integration tests for authentication and authorization."""

import uuid
from datetime import datetime, timedelta, timezone
from http import HTTPStatus
from typing import Any

import jwt
from fastapi.testclient import TestClient

from nutrition_tracking_api.api.schemas.auth.user import UserOut
from nutrition_tracking_api.api.services.auth.role import RoleService
from nutrition_tracking_api.orm.choices.history import HistoryActionEnum
from nutrition_tracking_api.orm.models.auth import Policy, Role, User
from nutrition_tracking_api.settings import settings
from tests.factories.auth.policy import PolicyFactory
from tests.factories.auth.role import RoleFactory, RolePayloadFactory
from tests.factories.auth.user import UserFactory

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_expired_access_token(user_id: str, username: str) -> str:
    """Создать JWT access токен с истекшим сроком жизни."""
    payload = {
        "sub": str(user_id),
        "username": username,
        "type": "access",
        "exp": datetime.now(tz=timezone.utc) - timedelta(hours=1),
        "iat": datetime.now(tz=timezone.utc) - timedelta(hours=2),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def _make_wrong_signature_token(user_id: str, username: str) -> str:
    """Создать JWT подписанный неправильным ключом."""
    payload = {
        "sub": str(user_id),
        "username": username,
        "type": "access",
        "exp": datetime.now(tz=timezone.utc) + timedelta(minutes=30),
        "iat": datetime.now(tz=timezone.utc),
    }
    return jwt.encode(payload, "wrong-secret-key-at-least-32-chars", algorithm="HS256")


# ---------------------------------------------------------------------------
# Тесты JWT-аутентификации
# ---------------------------------------------------------------------------


def test_auth_existing_user(client: TestClient, user: User) -> None:
    """Пользователь существует в БД. Токен валиден (не истёк)."""
    resp = client.get(
        "/auth/users/me/",
        headers={"Authorization": f"Bearer {user.access_token}"},
    )

    assert resp.status_code == HTTPStatus.OK
    assert resp.json()["id"] == str(user.id)


def test_expired_token_authentication(client: TestClient, user: User) -> None:
    """JWT с истекшим exp → 401."""
    expired_token = _make_expired_access_token(str(user.id), user.username)

    resp = client.get(
        "/auth/users/me/",
        headers={"Authorization": f"Bearer {expired_token}"},
    )

    assert resp.status_code == HTTPStatus.UNAUTHORIZED
    assert resp.json() == {"detail": "Токен авторизации истек"}


def test_invalid_signature_token(client: TestClient, user: User) -> None:
    """JWT подписан неправильным ключом → 401."""
    bad_token = _make_wrong_signature_token(str(user.id), user.username)

    resp = client.get(
        "/auth/users/me/",
        headers={"Authorization": f"Bearer {bad_token}"},
    )

    assert resp.status_code == HTTPStatus.UNAUTHORIZED


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


def test_get_me(client: TestClient, nutrition_user: User) -> None:
    """GET /auth/users/me/ возвращает текущего пользователя с профилем."""
    resp = client.get(
        "/auth/users/me/",
        headers={"Authorization": f"Bearer {nutrition_user.access_token}"},
    )

    assert resp.status_code == HTTPStatus.OK
    data = resp.json()
    assert data["id"] == str(nutrition_user.id)
    assert data["username"] == nutrition_user.username
    assert "birth_date" in data
    assert "height_cm" in data
    assert "weight_kg" in data


def test_rbac_or_between_policies(
    client: TestClient,
    make_user_with_permissions: Any,
    test_role_service: RoleService,
) -> None:
    """OR между политиками: если хотя бы одна политика разрешает — доступ открыт.

    User A имеет Политику 1 (matcher id=$user.id) — видит только себя.
    Добавляем Политику 2 без матчеров на ту же роль.
    OR: Политика 2 разрешает всё → User A теперь видит всех пользователей.
    """
    UserFactory()  # посторонний пользователь в БД

    user_a: UserOut = make_user_with_permissions(
        targets=["/auth/users/", "/auth/users/{object_id}"],
        actions=["GET"],
        matchers=[{"field": "id", "condition": "eq", "value": "$user.id"}],
    )

    # С одной политикой — видит только себя
    resp = client.get("/auth/users/", headers={"Authorization": f"Bearer {user_a.access_token}"})
    assert resp.status_code == HTTPStatus.OK
    assert resp.json()["count"] == 1

    # Добавляем вторую политику без матчеров (OR)
    open_policy: Policy = PolicyFactory(  # type: ignore[assignment]
        targets=["/auth/users/", "/auth/users/{object_id}"],
        actions=["GET"],
        matchers=None,
    )
    test_role_service.add_policy(role_id=user_a.roles[0].id, policy_id=open_policy.id)
    test_role_service.resource_crud.session.expire_all()

    # После OR с открытой политикой — видит всех (себя + постороннего)
    resp2 = client.get("/auth/users/", headers={"Authorization": f"Bearer {user_a.access_token}"})
    assert resp2.status_code == HTTPStatus.OK
    assert resp2.json()["count"] == 2


def test_rbac_and_within_policy(
    client: TestClient,
    make_user_with_permissions: Any,
) -> None:
    """AND внутри политики: запись должна удовлетворять всем матчерам одновременно.

    Политика с двумя матчерами (id=$user.id AND username=$user.username)
    разрешает только записи, где оба условия выполнены — то есть только сам пользователь.
    """
    UserFactory()  # посторонний пользователь в БД

    user_a: UserOut = make_user_with_permissions(
        targets=["/auth/users/", "/auth/users/{object_id}"],
        actions=["GET"],
        matchers=[
            {"field": "id", "condition": "eq", "value": "$user.id"},
            {"field": "username", "condition": "eq", "value": "$user.username"},
        ],
    )

    resp = client.get("/auth/users/", headers={"Authorization": f"Bearer {user_a.access_token}"})
    assert resp.status_code == HTTPStatus.OK
    # Оба матчера указывают на User A → видит только себя, несмотря на два условия
    assert resp.json()["count"] == 1
    assert resp.json()["items"][0]["id"] == str(user_a.id)


# ---------------------------------------------------------------------------
# Тесты register / login / refresh / logout
# ---------------------------------------------------------------------------

_PROFILE = {
    "birth_date": "1995-03-20",
    "gender": "male",
    "height_cm": 175.0,
    "weight_kg": 70.0,
    "activity_level": "moderately_active",
}


def test_register(client: TestClient) -> None:
    """Публичная регистрация создаёт пользователя и возвращает пару токенов."""
    payload = {"username": "newuser", "password": "securepass123", **_PROFILE}
    resp = client.post("/auth/register/", json=payload)

    assert resp.status_code == HTTPStatus.CREATED
    data = resp.json()
    assert data["access_token"]
    assert data["refresh_token"]
    assert data["token_type"] == "bearer"
    assert data["expires_in"] == settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60


def test_register_duplicate_username(client: TestClient) -> None:
    """Повторная регистрация с тем же именем → 400."""
    UserFactory(username="existinguser")
    payload = {"username": "existinguser", "password": "securepass123", **_PROFILE}
    resp = client.post("/auth/register/", json=payload)

    assert resp.status_code == HTTPStatus.BAD_REQUEST


def test_login_success(client: TestClient) -> None:
    """Логин с правильным паролем возвращает токены."""
    from nutrition_tracking_api.api.utils.auth import hash_password

    UserFactory(username="loginuser", password_hash=hash_password("mypassword123"))

    resp = client.post("/auth/login/", json={"username": "loginuser", "password": "mypassword123"})

    assert resp.status_code == HTTPStatus.OK
    data = resp.json()
    assert data["access_token"]
    assert data["refresh_token"]


def test_login_wrong_password(client: TestClient) -> None:
    """Логин с неправильным паролем → 401."""
    from nutrition_tracking_api.api.utils.auth import hash_password

    UserFactory(username="loginuser2", password_hash=hash_password("correctpassword"))

    resp = client.post("/auth/login/", json={"username": "loginuser2", "password": "wrongpassword"})

    assert resp.status_code == HTTPStatus.UNAUTHORIZED


def test_login_nonexistent_user(client: TestClient) -> None:
    """Логин с несуществующим пользователем → 401."""
    resp = client.post("/auth/login/", json={"username": "ghost", "password": "anypassword"})

    assert resp.status_code == HTTPStatus.UNAUTHORIZED


def test_refresh_token(client: TestClient) -> None:
    """Refresh токен обменивается на новую пару токенов (token rotation)."""
    # Регистрируемся чтобы получить refresh token
    resp = client.post("/auth/register/", json={"username": "refreshuser", "password": "pass12345", **_PROFILE})
    assert resp.status_code == HTTPStatus.CREATED
    refresh_token = resp.json()["refresh_token"]

    # Обмениваем refresh token
    resp2 = client.post("/auth/token/refresh/", json={"refresh_token": refresh_token})

    assert resp2.status_code == HTTPStatus.OK
    new_data = resp2.json()
    assert new_data["access_token"]
    assert new_data["refresh_token"]

    # Старый refresh token теперь отозван — нельзя использовать снова
    resp3 = client.post("/auth/token/refresh/", json={"refresh_token": refresh_token})
    assert resp3.status_code == HTTPStatus.UNAUTHORIZED


def test_refresh_token_used_twice(client: TestClient) -> None:
    """Использованный refresh токен нельзя использовать повторно → 401."""
    resp = client.post("/auth/register/", json={"username": "rotation_user", "password": "pass12345", **_PROFILE})
    refresh_token = resp.json()["refresh_token"]

    # Первое использование — успех
    resp2 = client.post("/auth/token/refresh/", json={"refresh_token": refresh_token})
    assert resp2.status_code == HTTPStatus.OK

    # Второе использование — старый токен уже отозван
    resp3 = client.post("/auth/token/refresh/", json={"refresh_token": refresh_token})
    assert resp3.status_code == HTTPStatus.UNAUTHORIZED


def test_logout(client: TestClient) -> None:
    """Logout отзывает refresh токен — дальнейший refresh невозможен."""
    resp = client.post("/auth/register/", json={"username": "logoutuser", "password": "pass12345", **_PROFILE})
    refresh_token = resp.json()["refresh_token"]

    # Logout
    resp_logout = client.post("/auth/logout/", json={"refresh_token": refresh_token})
    assert resp_logout.status_code == HTTPStatus.NO_CONTENT

    # Refresh после logout → 401
    resp_refresh = client.post("/auth/token/refresh/", json={"refresh_token": refresh_token})
    assert resp_refresh.status_code == HTTPStatus.UNAUTHORIZED


def test_access_token_valid_after_register(client: TestClient) -> None:
    """Access token полученный при регистрации работает для защищённых endpoints."""
    RoleFactory(is_default=True)
    resp = client.post("/auth/register/", json={"username": "apiuser", "password": "pass12345", **_PROFILE})
    access_token = resp.json()["access_token"]

    # /auth/users/me/ доступен без дополнительных прав
    resp_me = client.get(
        "/auth/users/me/",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert resp_me.status_code == HTTPStatus.OK
    assert resp_me.json()["username"] == "apiuser"


# ---------------------------------------------------------------------------
# Тесты CRUD: роли, политики, история
# ---------------------------------------------------------------------------


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


def test_update_profile_success(client: TestClient, nutrition_user: User) -> None:
    """Пользователь может обновить все поля профиля."""
    payload = {
        "birth_date": "1990-05-15",
        "gender": "male",
        "height_cm": 180.0,
        "weight_kg": 75.0,
        "activity_level": "moderately_active",
    }
    resp = client.patch(
        "/auth/users/me/",
        json=payload,
        headers={"Authorization": f"Bearer {nutrition_user.access_token}"},
    )
    assert resp.status_code == HTTPStatus.OK, resp.json()
    assert resp.json()["height_cm"] == 180.0
    assert resp.json()["weight_kg"] == 75.0
    assert resp.json()["gender"] == "male"
    assert resp.json()["birth_date"] == "1990-05-15"
    assert resp.json()["activity_level"] == "moderately_active"


def test_update_profile_partial(client: TestClient, nutrition_user: User) -> None:
    """Частичное обновление профиля — незаполненные поля остаются None."""
    resp = client.patch(
        "/auth/users/me/",
        json={"weight_kg": 80.0},
        headers={"Authorization": f"Bearer {nutrition_user.access_token}"},
    )
    assert resp.status_code == HTTPStatus.OK, resp.json()
    assert resp.json()["weight_kg"] == 80.0
    assert resp.json()["height_cm"] == 175.0  # не трогали — осталось из UserFactory


def test_update_profile_invalid_height(client: TestClient, nutrition_user: User) -> None:
    """Невалидное значение height_cm возвращает 422."""
    resp = client.patch(
        "/auth/users/me/",
        json={"height_cm": -1.0},
        headers={"Authorization": f"Bearer {nutrition_user.access_token}"},
    )
    assert resp.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


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
