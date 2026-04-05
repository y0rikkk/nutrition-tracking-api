import datetime
from http import HTTPStatus

from fastapi.testclient import TestClient

from nutrition_tracking_api.api.schemas.nutrition.meal_entry import MealEntryCreate, MealTypeEnum
from nutrition_tracking_api.orm.models.auth import User
from tests.factories.nutrition.meal_entry import MealEntryFactory


def test_create_meal_entry_simple(
    client: TestClient, meal_entry_payload: MealEntryCreate, nutrition_user: User
) -> None:
    """MealEntry требует bearer auth — user_id берётся из токена."""
    meal_entry_payload.user_id = None
    result = client.post(
        "/meals/",
        content=meal_entry_payload.model_dump_json(),
        headers={"Authorization": f"Bearer {nutrition_user.access_token}"},  # type: ignore[attr-defined]
    )
    assert result.status_code == HTTPStatus.CREATED, result.json()
    assert result.json()["id"]
    assert result.json()["user_id"] == str(nutrition_user.id)


def test_get_foods_by_filters(client: TestClient) -> None:
    obj_1 = MealEntryFactory(meal_type=MealTypeEnum.breakfast)
    _ = MealEntryFactory(meal_type=MealTypeEnum.snack)

    resp_all = client.get("/meals/").json()
    assert resp_all["count"] == 2

    resp_filtered = client.get("/meals/", params={"meal_type": "breakfast"}).json()
    assert resp_filtered["count"] == 1
    assert resp_filtered["items"][0]["id"] == str(obj_1.id)


def test_create_meal_entry_with_foreign_user_id_forbidden(client: TestClient, nutrition_user: User, user: User) -> None:
    """Обычный пользователь не может создать meal_entry с чужим user_id — 403.

    После создания base service делает self.get() с matcher user_id=$user.id,
    запись не находится (user_id чужого пользователя) → AccessDeniedError → 403.
    """
    payload = {
        "date": str(datetime.datetime.now().date()),
        "meal_type": "lunch",
        "source": "manual",
        "user_id": str(user.id),
    }
    result = client.post(
        "/meals/",
        json=payload,
        headers={"Authorization": f"Bearer {nutrition_user.access_token}"},  # type: ignore[attr-defined]
    )
    assert result.status_code == HTTPStatus.FORBIDDEN


def test_superuser_can_create_meal_entry_for_other_user(client: TestClient, superuser: User, user: User) -> None:
    """Суперюзер может создать meal_entry с произвольным user_id."""
    payload = {
        "date": str(datetime.datetime.now().date()),
        "meal_type": "lunch",
        "source": "manual",
        "user_id": str(user.id),
    }
    result = client.post(
        "/meals/",
        json=payload,
        headers={"Authorization": f"Bearer {superuser.access_token}"},  # type: ignore[attr-defined]
    )
    assert result.status_code == HTTPStatus.CREATED, result.json()
    assert result.json()["user_id"] == str(user.id)
