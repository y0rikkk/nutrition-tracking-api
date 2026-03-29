"""Nutrition domain ORM models."""

from sqlalchemy.orm import Mapped, mapped_column

from nutrition_tracking_api.orm.models.base import Base


class FoodItem(Base):
    """Продукт питания из базы КБЖУ."""

    name: Mapped[str] = mapped_column(index=True)
    brand: Mapped[str | None]
    calories_per_100g: Mapped[float]
    protein_per_100g: Mapped[float]
    fat_per_100g: Mapped[float]
    carbs_per_100g: Mapped[float]
    barcode: Mapped[str | None] = mapped_column(unique=True)
