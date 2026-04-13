"""Сервис для Dashboard."""

import datetime as dt

from sqlalchemy.orm import Session

from nutrition_tracking_api.api.schemas.auth.common import PermissionRules
from nutrition_tracking_api.api.schemas.auth.user import UserOut
from nutrition_tracking_api.api.schemas.nutrition.dashboard import (
    DashboardOut,
    GoalProgress,
    MacroProgress,
    MacroTotals,
    MealBreakdown,
)
from nutrition_tracking_api.api.schemas.nutrition.meal_entry import MealEntryDetailOut, MealTypeEnum
from nutrition_tracking_api.api.schemas.nutrition.meal_food_item import MealFoodItemOut
from nutrition_tracking_api.api.schemas.nutrition.nutrition_goal import NutritionGoalOut
from nutrition_tracking_api.api.services.nutrition.meal_entry import MealEntryService
from nutrition_tracking_api.api.services.nutrition.nutrition_goal import NutritionGoalService
from nutrition_tracking_api.app_schemas import RequestState


class DashboardService:
    """Агрегирует данные питания за день из существующих сервисов."""

    def __init__(
        self,
        session: Session,
        user: UserOut | None = None,
        rules: list[PermissionRules] | None = None,
        request_state: RequestState | None = None,
    ) -> None:
        self.meal_service = MealEntryService(session, rules, user, request_state)
        self.goal_service = NutritionGoalService(session, rules, user, request_state)

    def get_dashboard(self, date: dt.date) -> DashboardOut:
        """Собрать дашборд за указанную дату."""
        meals = self.meal_service.get_daily_meals(date)
        active_goal = self.goal_service.get_active_goal()

        all_items = [item for meal in meals for item in meal.items]
        consumed = self._sum_macros(all_items)

        return DashboardOut(
            date=date,
            consumed=consumed,
            goal=active_goal,
            goal_progress=self._compute_goal_progress(consumed, active_goal) if active_goal else None,
            meal_breakdown=self._compute_meal_breakdown(meals),
            meals=meals,
        )

    def _sum_macros(self, items: list[MealFoodItemOut]) -> MacroTotals:
        """Суммировать КБЖУ по списку позиций."""
        return MacroTotals(
            calories_kcal=round(sum(i.calories_kcal for i in items), 2),
            protein_g=round(sum(i.protein_g for i in items), 2),
            fat_g=round(sum(i.fat_g for i in items), 2),
            carbs_g=round(sum(i.carbs_g for i in items), 2),
        )

    def _compute_goal_progress(self, consumed: MacroTotals, goal: NutritionGoalOut) -> GoalProgress:
        """Вычислить прогресс по каждому макронутриенту относительно цели."""

        def _progress(consumed_val: float, goal_val: float) -> MacroProgress:
            return MacroProgress(
                consumed=consumed_val,
                goal=goal_val,
                remaining=round(goal_val - consumed_val, 2),
                percent=round(consumed_val / goal_val * 100, 1) if goal_val > 0 else 0.0,
            )

        return GoalProgress(
            calories=_progress(consumed.calories_kcal, goal.calories_kcal),
            protein=_progress(consumed.protein_g, goal.protein_g),
            fat=_progress(consumed.fat_g, goal.fat_g),
            carbs=_progress(consumed.carbs_g, goal.carbs_g),
        )

    def _compute_meal_breakdown(self, meals: list[MealEntryDetailOut]) -> list[MealBreakdown]:
        """Сгруппировать КБЖУ по типам приёма пищи (только присутствующие типы)."""
        totals_by_type: dict[MealTypeEnum, dict[str, float]] = {}
        order = [MealTypeEnum.breakfast, MealTypeEnum.lunch, MealTypeEnum.dinner, MealTypeEnum.snack]

        for meal in meals:
            key = meal.meal_type
            if key not in totals_by_type:
                totals_by_type[key] = {"calories_kcal": 0, "protein_g": 0, "fat_g": 0, "carbs_g": 0}
            for item in meal.items:
                totals_by_type[key]["calories_kcal"] += item.calories_kcal
                totals_by_type[key]["protein_g"] += item.protein_g
                totals_by_type[key]["fat_g"] += item.fat_g
                totals_by_type[key]["carbs_g"] += item.carbs_g

        return [
            MealBreakdown(
                meal_type=meal_type,
                totals=MacroTotals(
                    calories_kcal=round(totals_by_type[meal_type]["calories_kcal"], 2),
                    protein_g=round(totals_by_type[meal_type]["protein_g"], 2),
                    fat_g=round(totals_by_type[meal_type]["fat_g"], 2),
                    carbs_g=round(totals_by_type[meal_type]["carbs_g"], 2),
                ),
            )
            for meal_type in order
            if meal_type in totals_by_type
        ]
