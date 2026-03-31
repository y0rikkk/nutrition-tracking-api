"""Pydantic схемы для MealFoodItem."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from nutrition_tracking_api.api.schemas.filters import BasePaginationFilter


class MealFoodItemCreate(BaseModel):
    """Схема для добавления продукта в приём пищи."""

    meal_entry_id: UUID | None = None  # Устанавливается из URL path
    food_item_id: UUID | None = None
    custom_name: str | None = None
    amount_g: float = Field(..., gt=0)
    calories_kcal: float | None = Field(None, ge=0)  # Авто-расчёт если food_item_id указан
    protein_g: float | None = Field(None, ge=0)
    fat_g: float | None = Field(None, ge=0)
    carbs_g: float | None = Field(None, ge=0)

    @model_validator(mode="after")
    def validate_entry_type(self) -> "MealFoodItemCreate":
        """Валидация: при ручном вводе custom_name и все КБЖУ обязательны."""
        if self.food_item_id is None:
            if not self.custom_name:
                raise ValueError("custom_name обязателен при ручном вводе")  # noqa: TRY003 EM101
            if any(v is None for v in [self.calories_kcal, self.protein_g, self.fat_g, self.carbs_g]):
                raise ValueError("Все значения КБЖУ обязательны при ручном вводе")  # noqa: TRY003 EM101
        return self


class MealFoodItemUpdate(BaseModel):
    """Схема для обновления продукта в приёме пищи."""

    custom_name: str | None = None
    amount_g: float | None = Field(None, gt=0)
    calories_kcal: float | None = Field(None, ge=0)
    protein_g: float | None = Field(None, ge=0)
    fat_g: float | None = Field(None, ge=0)
    carbs_g: float | None = Field(None, ge=0)

    model_config = ConfigDict(extra="forbid")


class MealFoodItemOut(BaseModel):
    """Схема для вывода продукта в приёме пищи."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    meal_entry_id: UUID
    food_item_id: UUID | None
    custom_name: str | None
    amount_g: float
    calories_kcal: float
    protein_g: float
    fat_g: float
    carbs_g: float
    created_at: datetime
    updated_at: datetime


@dataclass
class MealFoodItemFilter(BasePaginationFilter):
    """Фильтры для продуктов в приёмах пищи."""

    meal_entry_id: UUID | None = None
