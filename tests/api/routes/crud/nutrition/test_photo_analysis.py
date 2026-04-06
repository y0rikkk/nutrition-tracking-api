"""Тесты эндпоинта POST /foods/analyze-photo/."""

import json
from http import HTTPStatus
from typing import TYPE_CHECKING

from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

if TYPE_CHECKING:
    from nutrition_tracking_api.orm.models.auth import User

_OPENROUTER_CHAT = "nutrition_tracking_api.integrations.openrouter.OpenRouterClient.chat"

_VALID_RESPONSE = json.dumps(
    {
        "dishes": [
            {"name": "Овсянка", "amount_g": 200, "calories_kcal": 176, "protein_g": 6.0, "fat_g": 3.4, "carbs_g": 30.0},
            {"name": "Банан", "amount_g": 120, "calories_kcal": 107, "protein_g": 1.3, "fat_g": 0.4, "carbs_g": 27.6},
        ]
    }
)

_FAKE_JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 16  # минимальный JPEG-заголовок


def _headers(user: "User") -> dict[str, str]:
    return {"Authorization": f"Bearer {user.access_token}"}  # type: ignore[attr-defined]


def _upload(client: TestClient, user: "User", content: bytes, content_type: str = "image/jpeg") -> object:
    return client.post(
        "/foods/analyze-photo/",
        headers=_headers(user),
        files={"photo": ("food.jpg", content, content_type)},
    )


def test_analyze_photo_returns_dishes(
    client: TestClient,
    nutrition_user: "User",
    mocker: MockerFixture,
) -> None:
    """Корректное фото → список блюд с КБЖУ."""
    mocker.patch(_OPENROUTER_CHAT, return_value=_VALID_RESPONSE)

    resp = _upload(client, nutrition_user, _FAKE_JPEG)

    assert resp.status_code == HTTPStatus.OK  # type: ignore[attr-defined]
    data = resp.json()  # type: ignore[attr-defined]
    assert len(data["dishes"]) == 2
    assert data["dishes"][0]["name"] == "Овсянка"
    assert data["dishes"][0]["calories_kcal"] == 176


def test_analyze_photo_strips_markdown_fences(
    client: TestClient,
    nutrition_user: "User",
    mocker: MockerFixture,
) -> None:
    """LLM вернул JSON в markdown-обёртке → парсится корректно."""
    mocker.patch(_OPENROUTER_CHAT, return_value=f"```json\n{_VALID_RESPONSE}\n```")

    resp = _upload(client, nutrition_user, _FAKE_JPEG)

    assert resp.status_code == HTTPStatus.OK  # type: ignore[attr-defined]
    data = resp.json()  # type: ignore[attr-defined]
    assert len(data["dishes"]) == 2
    assert data["dishes"][0]["name"] == "Овсянка"
    assert data["dishes"][0]["calories_kcal"] == 176


def test_analyze_photo_invalid_json_returns_422(
    client: TestClient,
    nutrition_user: "User",
    mocker: MockerFixture,
) -> None:
    """LLM вернул не-JSON → 422."""
    mocker.patch(_OPENROUTER_CHAT, return_value="Извините, не могу определить блюда.")

    resp = _upload(client, nutrition_user, _FAKE_JPEG)

    assert resp.status_code == HTTPStatus.UNPROCESSABLE_ENTITY  # type: ignore[attr-defined]
    assert "распознать" in resp.json()["detail"]  # type: ignore[attr-defined]


def test_analyze_photo_empty_dishes_returns_422(
    client: TestClient,
    nutrition_user: "User",
    mocker: MockerFixture,
) -> None:
    """LLM вернул пустой список блюд → 422."""
    mocker.patch(_OPENROUTER_CHAT, return_value=json.dumps({"dishes": []}))

    resp = _upload(client, nutrition_user, _FAKE_JPEG)

    assert resp.status_code == HTTPStatus.UNPROCESSABLE_ENTITY  # type: ignore[attr-defined]


def test_analyze_photo_unsupported_format_returns_422(
    client: TestClient,
    nutrition_user: "User",
) -> None:
    """Неподдерживаемый формат файла → 422."""
    resp = _upload(client, nutrition_user, b"GIF89a...", content_type="image/gif")

    assert resp.status_code == HTTPStatus.UNPROCESSABLE_ENTITY  # type: ignore[attr-defined]
    assert "jpeg" in resp.json()["detail"].lower()  # type: ignore[attr-defined]


def test_analyze_photo_requires_auth() -> None:
    """Без токена → 401."""
    from nutrition_tracking_api.api.main import app

    with TestClient(app) as unauthenticated_client:
        resp = unauthenticated_client.post(
            "/foods/analyze-photo/",
            files={"photo": ("food.jpg", _FAKE_JPEG, "image/jpeg")},
        )

    assert resp.status_code == HTTPStatus.UNAUTHORIZED
