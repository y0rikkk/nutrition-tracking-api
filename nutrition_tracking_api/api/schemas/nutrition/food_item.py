"""Pydantic схемы для FoodItem."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from nutrition_tracking_api.api.schemas.auth.common import UserShortOut
from nutrition_tracking_api.api.schemas.filters import BasePaginationFilter


class FoodItemCreate(BaseModel):
    """Схема для создания продукта питания."""

    name: str = Field(..., min_length=1, max_length=255)
    brand: str | None = None
    calories_per_100g: float = Field(..., ge=0)
    protein_per_100g: float = Field(..., ge=0)
    fat_per_100g: float = Field(..., ge=0)
    carbs_per_100g: float = Field(..., ge=0)
    barcode: str | None = None


class FoodItemUpdate(BaseModel):
    """Схема для обновления продукта питания."""

    name: str | None = Field(None, min_length=1, max_length=255)
    brand: str | None = None
    calories_per_100g: float | None = Field(None, ge=0)
    protein_per_100g: float | None = Field(None, ge=0)
    fat_per_100g: float | None = Field(None, ge=0)
    carbs_per_100g: float | None = Field(None, ge=0)
    barcode: str | None = None

    model_config = ConfigDict(extra="forbid")


class FoodItemOut(BaseModel):
    """Схема для вывода продукта питания."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    brand: str | None
    calories_per_100g: float
    protein_per_100g: float
    fat_per_100g: float
    carbs_per_100g: float
    barcode: str | None
    created_at: datetime
    updated_at: datetime
    creator: UserShortOut | None = None
    modifier: UserShortOut | None = None


@dataclass
class FoodItemFilter(BasePaginationFilter):
    """Фильтры для продуктов питания."""

    name__ilike: str | None = None
    brand__ilike: str | None = None
    barcode: str | None = None
