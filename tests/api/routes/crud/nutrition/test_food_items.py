from fastapi.testclient import TestClient

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
