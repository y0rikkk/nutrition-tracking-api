"""Специальные тесты для WeightLog: защита user_id."""

import datetime
from http import HTTPStatus

from fastapi.testclient import TestClient

from nutrition_tracking_api.orm.models.auth import User


def test_create_weight_log_with_foreign_user_id_forbidden(client: TestClient, nutrition_user: User, user: User) -> None:
    """Обычный пользователь не может создать лог веса с чужим user_id — 403."""
    payload = {
        "date": str(datetime.datetime.now().date()),
        "weight_kg": 80.0,
        "user_id": str(user.id),
    }
    result = client.post(
        "/weight-logs/",
        json=payload,
        headers={"Authorization": f"Bearer {nutrition_user.access_token}"},
    )
    assert result.status_code == HTTPStatus.FORBIDDEN
