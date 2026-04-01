"""Специальные тесты для NutritionGoal: авто-деактивация, запрет реактивации."""

import datetime
from http import HTTPStatus
from typing import Any

from fastapi.testclient import TestClient

from nutrition_tracking_api.orm.models.auth import User
from nutrition_tracking_api.orm.models.nutrition import NutritionGoal
from tests.factories.nutrition.nutrition_goal import NutritionGoalFactory


def test_create_auto_deactivates_previous_goal(client: TestClient, nutrition_user: User) -> None:
    """При создании новой цели предыдущая активная деактивируется автоматически."""
    first_goal = NutritionGoalFactory(user=nutrition_user, is_active=True)

    payload = {
        "calories_kcal": 1800.0,
        "protein_g": 120.0,
        "fat_g": 60.0,
        "carbs_g": 200.0,
        "started_at": str(datetime.datetime.now().date()),
    }
    result = client.post(
        "/goals/",
        json=payload,
        headers={"Authorization": f"Bearer {nutrition_user.access_token}"},
    )
    assert result.status_code == HTTPStatus.CREATED, result.json()
    new_goal_id = result.json()["id"]

    # Новая цель активна
    assert result.json()["is_active"] is True

    # Предыдущая цель деактивирована
    old_goal = client.get(f"/goals/{first_goal.id}").json()
    assert old_goal["is_active"] is False
    assert old_goal["ended_at"] == str(datetime.datetime.now().date())

    # Только одна активная цель
    active_goals = client.get("/goals/", params={"is_active": True}).json()
    assert active_goals["count"] == 1
    assert active_goals["items"][0]["id"] == new_goal_id


def test_update_deactivate_sets_ended_at(client: TestClient, nutrition_goal: User) -> None:
    """PATCH is_active=False проставляет ended_at=today."""
    resp = client.patch(f"/goals/{nutrition_goal.id}", json={"is_active": False})

    assert resp.status_code == HTTPStatus.OK, resp.json()
    assert resp.json()["is_active"] is False
    assert resp.json()["ended_at"] == str(datetime.datetime.now().date())


def test_update_reactivate_forbidden(client: TestClient, nutrition_user: User) -> None:
    """PATCH is_active=True на деактивированной цели → 422."""
    goal = NutritionGoalFactory(user=nutrition_user, is_active=False, ended_at=datetime.datetime.now().date())

    resp = client.patch(
        f"/goals/{goal.id}",
        json={"is_active": True},
        headers={"Authorization": f"Bearer {nutrition_user.access_token}"},
    )
    assert resp.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


def test_create_goal_with_foreign_user_id_forbidden(client: TestClient, nutrition_user: User, user: User) -> None:
    """Обычный пользователь не может создать цель с чужим user_id — 403."""
    payload = {
        "calories_kcal": 2000.0,
        "protein_g": 150.0,
        "fat_g": 70.0,
        "carbs_g": 250.0,
        "started_at": str(datetime.datetime.now().date()),
        "user_id": str(user.id),
    }
    result = client.post(
        "/goals/",
        json=payload,
        headers={"Authorization": f"Bearer {nutrition_user.access_token}"},
    )
    assert result.status_code == HTTPStatus.FORBIDDEN


def test_foreign_user_id_does_not_deactivate_any_goals(
    client: TestClient,
    nutrition_user: User,
    make_user_with_permissions: Any,
) -> None:
    """Неудачная попытка создать цель с чужим user_id не деактивирует ничьи цели.

    Проверяем три вещи:
    - Злоумышленник получает 403
    - Активная цель жертвы остаётся нетронутой (транзакция откатывается)
    - Собственная активная цель злоумышленника тоже не деактивируется
    """
    victim_goal = NutritionGoalFactory(user=nutrition_user, is_active=True)

    attacker = make_user_with_permissions(
        targets=["/goals/", "/goals/{object_id}"],
        actions=["GET", "POST", "PATCH", "DELETE"],
        matchers=[{"field": "user_id", "condition": "eq", "value": "$user.id"}],
    )
    attacker_goal = NutritionGoalFactory(user_id=attacker.id, is_active=True)

    payload = {
        "calories_kcal": 1800.0,
        "protein_g": 100.0,
        "fat_g": 50.0,
        "carbs_g": 200.0,
        "started_at": str(datetime.datetime.now().date()),
        "user_id": str(nutrition_user.id),
    }
    result = client.post(
        "/goals/",
        json=payload,
        headers={"Authorization": f"Bearer {attacker.access_token}"},
    )
    assert result.status_code == HTTPStatus.FORBIDDEN

    # Активная цель жертвы не тронута
    victim_goal_resp = client.get(f"/goals/{victim_goal.id}")
    assert victim_goal_resp.json()["is_active"] is True
    assert victim_goal_resp.json()["ended_at"] is None

    # Собственная цель злоумышленника тоже не деактивирована
    attacker_goal_resp = client.get(f"/goals/{attacker_goal.id}")
    assert attacker_goal_resp.json()["is_active"] is True
    assert attacker_goal_resp.json()["ended_at"] is None


def test_update_deactivate_custom_ended_at_overridden(
    client: TestClient,
    nutrition_goal: NutritionGoal,
) -> None:
    """Переданный ended_at при деактивации перезаписывается на today сервисом."""
    custom_date = "2020-01-01"

    resp = client.patch(f"/goals/{nutrition_goal.id}", json={"is_active": False, "ended_at": custom_date})

    assert resp.status_code == HTTPStatus.OK, resp.json()
    assert resp.json()["is_active"] is False
    assert resp.json()["ended_at"] == str(datetime.datetime.now().date())
    assert resp.json()["ended_at"] != custom_date
