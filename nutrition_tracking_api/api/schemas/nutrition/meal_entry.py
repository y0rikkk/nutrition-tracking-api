"""Pydantic схемы для MealEntry."""

import datetime
from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from nutrition_tracking_api.api.schemas.filters import BasePaginationFilter
from nutrition_tracking_api.api.schemas.nutrition.meal_food_item import MealFoodItemOut


class MealTypeEnum(StrEnum):
    """Тип приёма пищи."""

    breakfast = "breakfast"
    lunch = "lunch"
    dinner = "dinner"
    snack = "snack"


class MealSourceEnum(StrEnum):
    """Источник данных о приёме пищи."""

    manual = "manual"
    photo = "photo"


class MealEntryCreate(BaseModel):
    """Схема для создания приёма пищи."""

    date: datetime.date
    meal_type: MealTypeEnum
    notes: str | None = None
    source: MealSourceEnum = MealSourceEnum.manual
    photo_url: str | None = None
    user_id: UUID | None = None  # Устанавливается сервером из токена


class MealEntryUpdate(BaseModel):
    """Схема для обновления приёма пищи."""

    notes: str | None = None

    model_config = ConfigDict(extra="forbid")


class MealEntryOut(BaseModel):
    """Схема для вывода приёма пищи (список)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    date: datetime.date
    meal_type: MealTypeEnum
    notes: str | None
    source: MealSourceEnum
    photo_url: str | None
    created_at: datetime.datetime
    updated_at: datetime.datetime


class MealEntryDetailOut(MealEntryOut):
    """Схема для детального вывода приёма пищи (с продуктами)."""

    items: list[MealFoodItemOut] = []


@dataclass
class MealEntryFilter(BasePaginationFilter):
    """Фильтры для приёмов пищи."""

    date: datetime.date | None = None
    meal_type: MealTypeEnum | None = None
    source: MealSourceEnum | None = None
    user_id: UUID | None = None
