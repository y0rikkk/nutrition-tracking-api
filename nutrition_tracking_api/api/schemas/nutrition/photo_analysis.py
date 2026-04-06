"""Pydantic схемы для анализа фото блюд."""

from pydantic import BaseModel, Field


class RecognizedDish(BaseModel):
    """Распознанное блюдо с оценкой КБЖУ."""

    name: str
    amount_g: float = Field(gt=0)
    calories_kcal: float = Field(ge=0)
    protein_g: float = Field(ge=0)
    fat_g: float = Field(ge=0)
    carbs_g: float = Field(ge=0)


class PhotoAnalysisOut(BaseModel):
    """Результат анализа фото — список распознанных блюд."""

    dishes: list[RecognizedDish]
