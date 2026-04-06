"""Pydantic схемы для MealEntry."""

import datetime
from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, computed_field

from nutrition_tracking_api.api.schemas.filters import BasePaginationFilter
from nutrition_tracking_api.api.schemas.nutrition.meal_food_item import MealFoodItemOut


class MealTypeEnum(StrEnum):
    """Тип приёма пищи."""

    breakfast = "breakfast"
    lunch = "lunch"
    dinner = "dinner"
    snack = "snack"


class MealEntryCreate(BaseModel):
    """Схема для создания приёма пищи."""

    date: datetime.date
    meal_type: MealTypeEnum
    notes: str | None = None
    user_id: UUID | None = None  # Устанавливается сервером из токена


class MealEntryUpdate(BaseModel):
    """Схема для обновления приёма пищи."""

    notes: str | None = None

    model_config = ConfigDict(extra="forbid")


class MealEntryOut(BaseModel):
    """Схема для вывода приёма пищи (список).

    items загружаются через subqueryload в MealEntryCRUD, но скрыты из вывода.
    computed_field-поля считают суммы КБЖУ по items.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    date: datetime.date
    meal_type: MealTypeEnum
    notes: str | None
    created_at: datetime.datetime
    updated_at: datetime.datetime

    items: list[MealFoodItemOut] = Field(default=[], exclude=True)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def calories_kcal(self) -> float:
        return round(sum(i.calories_kcal for i in self.items), 2)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def protein_g(self) -> float:
        return round(sum(i.protein_g for i in self.items), 2)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def fat_g(self) -> float:
        return round(sum(i.fat_g for i in self.items), 2)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def carbs_g(self) -> float:
        return round(sum(i.carbs_g for i in self.items), 2)


class MealEntryDetailOut(MealEntryOut):
    """Схема для детального вывода приёма пищи (с продуктами)."""

    items: list[MealFoodItemOut] = []


@dataclass
class MealEntryFilter(BasePaginationFilter):
    """Фильтры для приёмов пищи."""

    date: datetime.date | None = None
    meal_type: MealTypeEnum | None = None
    user_id: UUID | None = None
