from http import HTTPStatus

from fastapi.testclient import TestClient

from nutrition_tracking_api.orm.models.auth import User
from tests.factories.nutrition.food_item import FoodItemFactory


def test_get_foods_by_filters(client: TestClient) -> None:
    obj_1 = FoodItemFactory(name="apple")
    obj_2 = FoodItemFactory(name="cola", brand="coca-cola")

    resp_all = client.get("/foods/").json()
    assert resp_all["count"] == 2

    resp_filtered_name = client.get("/foods/", params={"name__ilike": "apple"}).json()
    assert resp_filtered_name["count"] == 1
    assert resp_filtered_name["items"][0]["id"] == str(obj_1.id)

    resp_filtered_brand = client.get("/foods/", params={"brand__ilike": "coca-cola"}).json()
    assert resp_filtered_brand["count"] == 1
    assert resp_filtered_brand["items"][0]["id"] == str(obj_2.id)


def test_delete_own_food_item(client: TestClient, nutrition_user: User) -> None:
    """Пользователь может удалить продукт, который сам создал."""
    food_item = FoodItemFactory(creator_id=nutrition_user.id)

    resp = client.delete(
        f"/foods/{food_item.id}",
        headers={"Authorization": f"Bearer {nutrition_user.access_token}"},
    )
    assert resp.status_code == HTTPStatus.OK

    resp_get = client.get(f"/foods/{food_item.id}")
    assert resp_get.status_code == HTTPStatus.NOT_FOUND


def test_delete_foreign_food_item_not_found(client: TestClient, nutrition_user: User) -> None:
    """Пользователь не может удалить чужой продукт — 404 (RBAC matcher creator_id=$user.id)."""
    foreign_food = FoodItemFactory()  # creator_id != nutrition_user.id

    resp = client.delete(
        f"/foods/{foreign_food.id}",
        headers={"Authorization": f"Bearer {nutrition_user.access_token}"},
    )
    assert resp.status_code == HTTPStatus.NOT_FOUND
