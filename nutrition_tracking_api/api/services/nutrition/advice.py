"""Сервис для получения диетологических советов через LLM."""

import datetime as dt

from sqlalchemy.orm import Session

from nutrition_tracking_api.api.schemas.auth.common import PermissionRules
from nutrition_tracking_api.api.schemas.auth.user import UserOut
from nutrition_tracking_api.api.schemas.nutrition.advice import AdviceOut, AdviceRequest
from nutrition_tracking_api.api.schemas.nutrition.nutrition_goal import NutritionGoalOut
from nutrition_tracking_api.api.schemas.nutrition.weight_log import WeightLogOut
from nutrition_tracking_api.api.services.nutrition.meal_entry import MealEntryService
from nutrition_tracking_api.api.services.nutrition.nutrition_goal import NutritionGoalService
from nutrition_tracking_api.api.services.nutrition.weight_log import WeightLogService
from nutrition_tracking_api.app_schemas import RequestState
from nutrition_tracking_api.integrations.openrouter import OpenRouterClient

_ACTIVITY_LABELS = {
    "sedentary": "малоподвижный",
    "lightly_active": "слабоактивный",
    "moderately_active": "умеренно активный",
    "very_active": "очень активный",
    "extra_active": "экстремально активный",
}

_GENDER_LABELS = {
    "male": "мужской",
    "female": "женский",
}

_SYSTEM_PROMPT = (
    "Ты персональный диетолог. Анализируй данные питания пользователя и давай конкретные, "
    "поддерживающие советы на русском языке. Отвечай кратко: 3-5 чётких пунктов без лишних вступлений."
)


class AdviceService:
    """Собирает контекст питания пользователя и получает совет от LLM."""

    def __init__(
        self,
        session: Session,
        user: UserOut | None = None,
        rules: list[PermissionRules] | None = None,
        request_state: RequestState | None = None,
    ) -> None:
        self.user: UserOut = user  # type: ignore[assignment]
        self.meal_service = MealEntryService(session, rules, user, request_state)
        self.goal_service = NutritionGoalService(session, rules, user, request_state)
        self.weight_service = WeightLogService(session, rules, user, request_state)

    def get_advice(self, request: AdviceRequest) -> AdviceOut:
        """Получить персональный совет по питанию."""
        active_goal = self.goal_service.get_active_goal()
        latest_weight = self.weight_service.get_latest()

        today = dt.datetime.now().date()
        daily_stats = []
        for offset in range(request.days):
            day = today - dt.timedelta(days=offset)
            meals = self.meal_service.get_daily_meals(day)
            if not meals:
                continue
            total_cal = round(sum(sum(i.calories_kcal for i in m.items) for m in meals), 1)
            total_prot = round(sum(sum(i.protein_g for i in m.items) for m in meals), 1)
            total_fat = round(sum(sum(i.fat_g for i in m.items) for m in meals), 1)
            total_carbs = round(sum(sum(i.carbs_g for i in m.items) for m in meals), 1)
            daily_stats.append(f"  {day}: {total_cal} ккал, Б {total_prot}г, Ж {total_fat}г, У {total_carbs}г")

        user_message = self._build_user_message(
            daily_stats=daily_stats,
            active_goal=active_goal,
            latest_weight=latest_weight,
            question=request.question,
        )

        advice_text = OpenRouterClient().chat(
            [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ]
        )
        return AdviceOut(advice=advice_text)

    def _build_user_message(
        self,
        daily_stats: list[str],
        active_goal: NutritionGoalOut | None,
        latest_weight: WeightLogOut | None,
        question: str | None,
    ) -> str:
        """Сформировать текст пользовательского сообщения с контекстом."""
        age = (dt.datetime.now().date() - self.user.birth_date).days // 365
        lines: list[str] = [
            "## Профиль пользователя",
            f"- Возраст: {age} лет",
            f"- Пол: {_GENDER_LABELS.get(self.user.gender, self.user.gender)}",
            f"- Рост: {self.user.height_cm} см",
            f"- Вес при регистрации: {self.user.weight_kg} кг",
            f"- Активность: {_ACTIVITY_LABELS.get(self.user.activity_level, self.user.activity_level)}",
        ]

        if latest_weight:
            lines.append(f"- Текущий вес: {latest_weight.weight_kg} кг (по данным от {latest_weight.date})")

        if active_goal:
            lines.append("\n## Цель по КБЖУ в день")
            lines.append(
                f"- Калории: {active_goal.calories_kcal} ккал, "
                f"Белки: {active_goal.protein_g}г, "
                f"Жиры: {active_goal.fat_g}г, "
                f"Углеводы: {active_goal.carbs_g}г"
            )
        else:
            lines.append("\n## Цель по КБЖУ: не задана")

        if daily_stats:
            lines.append("\n## Фактическое питание за последние дни")
            lines.extend(daily_stats)
        else:
            lines.append("\n## Фактическое питание: данных нет")

        if question:
            lines.append(f"\n## Вопрос пользователя\n{question}")
        else:
            lines.append("\n## Задача\nДай общие рекомендации по питанию на основе данных выше.")

        return "\n".join(lines)
