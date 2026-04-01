"""Pydantic схемы для WeightLog."""

import datetime
from dataclasses import dataclass
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from nutrition_tracking_api.api.schemas.filters import BasePaginationFilter


class WeightLogCreate(BaseModel):
    """Схема для создания записи веса."""

    date: datetime.date
    weight_kg: float = Field(..., gt=0)
    notes: str | None = None
    user_id: UUID | None = None  # инжектируется из токена в _handle_pre_create


class WeightLogUpdate(BaseModel):
    """Схема для обновления записи веса."""

    notes: str | None = None

    model_config = ConfigDict(extra="forbid")


class WeightLogOut(BaseModel):
    """Схема для вывода записи веса."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    date: datetime.date
    weight_kg: float
    notes: str | None
    created_at: datetime.datetime
    updated_at: datetime.datetime


@dataclass
class WeightLogFilter(BasePaginationFilter):
    """Фильтры для записей веса."""

    user_id: UUID | None = None
    date: datetime.date | None = None
    date__gte: datetime.date | None = None
    date__lte: datetime.date | None = None
