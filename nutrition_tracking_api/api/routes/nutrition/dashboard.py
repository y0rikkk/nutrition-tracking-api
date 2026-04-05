"""Роут для Dashboard."""

import datetime as dt
from typing import Annotated, Any

from fastapi import APIRouter, Query

from nutrition_tracking_api.api.schemas.nutrition.dashboard import DashboardOut
from nutrition_tracking_api.api.services.nutrition.dashboard import DashboardService
from nutrition_tracking_api.dependencies import (
    RequestStateDependency,
    RulesDependency,
    SessionDependency,
    UserDependency,
)

router = APIRouter(tags=["dashboard"], prefix="/dashboard")


@router.get(
    "/",
    summary="Дашборд питания на день",
    response_model=DashboardOut,
)
def get_dashboard(
    session: SessionDependency,
    rules: RulesDependency,
    user: UserDependency,
    request_state: RequestStateDependency,
    date: Annotated[dt.date, Query(default_factory=dt.date.today)],
) -> Any:
    """Агрегированные данные питания за указанный день."""
    return DashboardService(session, user, rules, request_state).get_dashboard(date)
