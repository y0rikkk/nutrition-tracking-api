"""Роут для получения диетологических советов."""

from typing import Any

from fastapi import APIRouter

from nutrition_tracking_api.api.schemas.nutrition.advice import AdviceOut, AdviceRequest
from nutrition_tracking_api.api.services.nutrition.advice import AdviceService
from nutrition_tracking_api.dependencies import (
    RequestStateDependency,
    RulesDependency,
    SessionDependency,
    UserDependency,
)

router = APIRouter(tags=["advice"], prefix="/advice")


@router.post(
    "/",
    summary="Получить персональный совет по питанию",
    response_model=AdviceOut,
)
def get_advice(
    session: SessionDependency,
    rules: RulesDependency,
    user: UserDependency,
    request_state: RequestStateDependency,
    body: AdviceRequest,
) -> Any:
    """Анализирует питание пользователя за последние N дней и возвращает совет от LLM."""
    return AdviceService(session, user, rules, request_state).get_advice(body)
