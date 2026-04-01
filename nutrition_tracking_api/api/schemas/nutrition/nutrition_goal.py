"""Pydantic схемы для NutritionGoal."""

import datetime
from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from nutrition_tracking_api.api.schemas.filters import BasePaginationFilter


class NutritionGoalCreate(BaseModel):
    """Схема для создания цели по КБЖУ."""

    calories_kcal: float = Field(..., gt=0)
    protein_g: float = Field(..., ge=0)
    fat_g: float = Field(..., ge=0)
    carbs_g: float = Field(..., ge=0)
    started_at: datetime.date
    notes: str | None = None
    user_id: UUID | None = None  # инжектируется из токена в _handle_pre_create


class NutritionGoalUpdate(BaseModel):
    """Схема для обновления цели по КБЖУ.

    is_active допускает только False (деактивация).
    Реактивация (False → True) запрещена — Pydantic вернёт 422.
    ended_at проставляется сервером автоматически при деактивации.
    """

    notes: str | None = None
    is_active: Literal[False] | None = None
    ended_at: datetime.date | None = None

    model_config = ConfigDict(extra="forbid")


class NutritionGoalOut(BaseModel):
    """Схема для вывода цели по КБЖУ."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    calories_kcal: float
    protein_g: float
    fat_g: float
    carbs_g: float
    is_active: bool
    started_at: datetime.date
    ended_at: datetime.date | None
    notes: str | None
    created_at: datetime.datetime
    updated_at: datetime.datetime


@dataclass
class NutritionGoalFilter(BasePaginationFilter):
    """Фильтры для целей по КБЖУ."""

    is_active: bool | None = None
    user_id: UUID | None = None
