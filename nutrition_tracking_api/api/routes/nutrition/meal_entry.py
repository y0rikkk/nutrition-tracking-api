"""Роуты для MealEntry."""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends

from nutrition_tracking_api.api.schemas.nutrition.meal_food_item import (
    MealFoodItemCreate,
    MealFoodItemFilter,
    MealFoodItemOut,
)
from nutrition_tracking_api.api.schemas.pagination import Page
from nutrition_tracking_api.api.services.nutrition.meal_entry import MealEntryService
from nutrition_tracking_api.api.services.nutrition.meal_food_item import MealFoodItemService
from nutrition_tracking_api.api.utils.routes import init_crud_routes
from nutrition_tracking_api.dependencies import (
    RequestStateDependency,
    RulesDependency,
    SessionDependency,
    UserDependency,
)

router = APIRouter(tags=["meal_entries"], prefix="/meals")

init_crud_routes(router, MealEntryService)


@router.get(
    "/{meal_entry_id}/items/",
    summary="Список продуктов в приёме пищи",
    response_model=Page[MealFoodItemOut],
)
def get_meal_items(  # noqa: PLR0913
    meal_entry_id: UUID,
    filters: Annotated[MealFoodItemFilter, Depends()],
    session: SessionDependency,
    rules: RulesDependency,
    user: UserDependency,
    request_state: RequestStateDependency,
) -> Any:
    filters.meal_entry_id = meal_entry_id
    items, count = MealFoodItemService(session, rules=rules, user=user, request_state=request_state).get_multi(filters)
    return Page(items=items, count=count)


@router.post(
    "/{meal_entry_id}/items/",
    summary="Добавить продукт в приём пищи",
    status_code=201,
    response_model=MealFoodItemOut,
)
def create_meal_item(  # noqa: PLR0913
    meal_entry_id: UUID,
    create_data: MealFoodItemCreate,
    session: SessionDependency,
    rules: RulesDependency,
    user: UserDependency,
    request_state: RequestStateDependency,
) -> Any:
    create_data.meal_entry_id = meal_entry_id
    return MealFoodItemService(session, rules=rules, user=user, request_state=request_state).create(create_data)
