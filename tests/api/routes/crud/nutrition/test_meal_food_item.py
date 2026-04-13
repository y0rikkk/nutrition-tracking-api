"""Специальные тесты для MealFoodItem."""

from http import HTTPStatus

from fastapi.testclient import TestClient

from nutrition_tracking_api.api.schemas.nutrition.meal_food_item import MealFoodItemCreate
from nutrition_tracking_api.orm.models.auth import User
from nutrition_tracking_api.orm.models.nutrition import FoodItem, MealEntry, MealFoodItem
from tests.factories.nutrition.meal_entry import MealEntryFactory


def test_create_meal_food_item_simple(
    client: TestClient, nutrition_user: User, meal_food_item_payload: MealFoodItemCreate
) -> None:
    """POST /meal-items/ — user владеет meal_entry, bearer auth."""
    from tests.factories.nutrition.meal_entry import MealEntryFactory

    meal_entry = MealEntryFactory(user=nutrition_user)
    meal_food_item_payload.meal_entry_id = meal_entry.id  # type: ignore[assignment]
    result = client.post(
        "/meal-items/",
        content=meal_food_item_payload.model_dump_json(),
        headers={"Authorization": f"Bearer {nutrition_user.access_token}"},  # type: ignore[attr-defined]
    )
    assert result.status_code == HTTPStatus.CREATED, result.json()
    assert result.json()["id"]
    assert result.json()["meal_entry_id"] == str(meal_entry.id)


def test_create_with_food_item_auto_calc(client: TestClient, nutrition_user: User, food_item: FoodItem) -> None:
    """КБЖУ рассчитывается автоматически если указан food_item_id."""
    meal_entry = MealEntryFactory(user=nutrition_user)
    payload = {
        "meal_entry_id": str(meal_entry.id),
        "food_item_id": str(food_item.id),
        "amount_g": 200.0,
    }
    result = client.post(
        "/meal-items/",
        json=payload,
        headers={"Authorization": f"Bearer {nutrition_user.access_token}"},  # type: ignore[attr-defined]
    )
    assert result.status_code == HTTPStatus.CREATED, result.json()

    data = result.json()
    assert data["food_item_id"] == str(food_item.id)
    assert data["name"] == food_item.name
    assert data["calories_kcal"] == round(food_item.calories_per_100g * 2, 2)
    assert data["protein_g"] == round(food_item.protein_per_100g * 2, 2)
    assert data["fat_g"] == round(food_item.fat_per_100g * 2, 2)
    assert data["carbs_g"] == round(food_item.carbs_per_100g * 2, 2)


def test_create_via_meal_convenience_endpoint(client: TestClient, nutrition_user: User) -> None:
    """POST /meals/{id}/items/ — meal_entry_id берётся из URL, не из тела."""
    meal_entry = MealEntryFactory(user=nutrition_user)
    payload = {
        "name": "Тарелка супа",
        "amount_g": 300.0,
        "calories_kcal": 120.0,
        "protein_g": 5.0,
        "fat_g": 3.0,
        "carbs_g": 15.0,
    }
    result = client.post(
        f"/meals/{meal_entry.id}/items/",
        json=payload,
        headers={"Authorization": f"Bearer {nutrition_user.access_token}"},  # type: ignore[attr-defined]
    )
    assert result.status_code == HTTPStatus.CREATED, result.json()
    assert result.json()["meal_entry_id"] == str(meal_entry.id)


def test_create_manual_without_name_fails(client: TestClient, meal_entry: MealEntry) -> None:
    """Ручной ввод без name должен вернуть 422 (Pydantic validation)."""
    payload = {
        "meal_entry_id": str(meal_entry.id),
        "amount_g": 100.0,
        "calories_kcal": 150.0,
        "protein_g": 10.0,
        "fat_g": 5.0,
        "carbs_g": 20.0,
    }
    result = client.post("/meal-items/", json=payload)
    assert result.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert "name обязателен при ручном вводе" in result.json()["detail"][0]["msg"]


def test_create_manual_without_kbju_fails(client: TestClient, meal_entry: MealEntry) -> None:
    """Ручной ввод без КБЖУ должен вернуть 422 (Pydantic validation)."""
    payload = {
        "meal_entry_id": str(meal_entry.id),
        "name": "Домашний суп",
        "amount_g": 300.0,
    }
    result = client.post("/meal-items/", json=payload)
    assert result.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert "Все значения КБЖУ обязательны при ручном вводе" in result.json()["detail"][0]["msg"]


def test_create_with_foreign_meal_entry_not_found(
    client: TestClient, nutrition_user: User, meal_entry: MealEntry
) -> None:
    """Нельзя добавить item в meal_entry другого пользователя — должен вернуть 403."""
    payload = {
        "meal_entry_id": str(meal_entry.id),
        "name": "Чужой суп",
        "amount_g": 100.0,
        "calories_kcal": 50.0,
        "protein_g": 2.0,
        "fat_g": 1.0,
        "carbs_g": 8.0,
    }
    result = client.post(
        "/meal-items/",
        json=payload,
        headers={"Authorization": f"Bearer {nutrition_user.access_token}"},  # type: ignore[attr-defined]
    )
    assert result.status_code == HTTPStatus.FORBIDDEN


def test_superuser_can_create_for_foreign_meal_entry(
    client: TestClient, superuser: User, meal_entry: MealEntry
) -> None:
    """Суперюзер может добавить item в meal_entry любого пользователя."""
    payload = {
        "meal_entry_id": str(meal_entry.id),
        "name": "Суп суперюзера",
        "amount_g": 100.0,
        "calories_kcal": 50.0,
        "protein_g": 2.0,
        "fat_g": 1.0,
        "carbs_g": 8.0,
    }
    result = client.post(
        "/meal-items/",
        json=payload,
        headers={"Authorization": f"Bearer {superuser.access_token}"},  # type: ignore[attr-defined]
    )
    assert result.status_code == HTTPStatus.CREATED, result.json()
    assert result.json()["meal_entry_id"] == str(meal_entry.id)


def test_get_meal_items_by_meal(client: TestClient, meal_food_item: MealFoodItem) -> None:
    """GET /meals/{id}/items/ — convenience endpoint фильтрует по meal_entry_id."""
    resp = client.get(f"/meals/{meal_food_item.meal_entry_id}/items/")
    assert resp.status_code == HTTPStatus.OK
    assert resp.json()["count"] == 1
    assert resp.json()["items"][0]["id"] == str(meal_food_item.id)


def test_get_meal_items_by_meal_empty(client: TestClient, meal_entry: MealEntry) -> None:
    resp = client.get(f"/meals/{meal_entry.id}/items/")
    assert resp.status_code == HTTPStatus.OK
    assert resp.json()["items"] == []
    assert resp.json()["count"] == 0
