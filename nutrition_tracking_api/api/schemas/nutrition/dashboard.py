"""Pydantic схемы для Dashboard."""

import datetime as dt

from pydantic import BaseModel, ConfigDict

from nutrition_tracking_api.api.schemas.nutrition.meal_entry import MealEntryDetailOut, MealTypeEnum
from nutrition_tracking_api.api.schemas.nutrition.nutrition_goal import NutritionGoalOut


class MacroTotals(BaseModel):
    """Суммарные макронутриенты."""

    calories_kcal: float
    protein_g: float
    fat_g: float
    carbs_g: float


class MacroProgress(BaseModel):
    """Прогресс по одному макронутриенту относительно цели."""

    consumed: float
    goal: float
    remaining: float  # goal - consumed (может быть отрицательным если превышено)
    percent: float  # consumed / goal * 100


class GoalProgress(BaseModel):
    """Прогресс по всем макронутриентам относительно активной цели."""

    calories: MacroProgress
    protein: MacroProgress
    fat: MacroProgress
    carbs: MacroProgress


class MealBreakdown(BaseModel):
    """Сводка по одному типу приёма пищи."""

    meal_type: MealTypeEnum
    totals: MacroTotals


class DashboardOut(BaseModel):
    """Дашборд питания за день."""

    model_config = ConfigDict(from_attributes=True)

    date: dt.date
    consumed: MacroTotals
    goal: NutritionGoalOut | None
    goal_progress: GoalProgress | None
    meal_breakdown: list[MealBreakdown]
    meals: list[MealEntryDetailOut]
