"""Nutrition domain ORM models."""

from datetime import date
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from nutrition_tracking_api.api.schemas.nutrition.meal_entry import MealSourceEnum, MealTypeEnum
from nutrition_tracking_api.orm.models.base import Base
from nutrition_tracking_api.orm.models.utils import make_enum_column_type

if TYPE_CHECKING:
    from nutrition_tracking_api.orm.models.auth import User


class FoodItem(Base):
    """Продукт питания из базы КБЖУ."""

    name: Mapped[str] = mapped_column(index=True)
    brand: Mapped[str | None]
    calories_per_100g: Mapped[float]
    protein_per_100g: Mapped[float]
    fat_per_100g: Mapped[float]
    carbs_per_100g: Mapped[float]
    barcode: Mapped[str | None] = mapped_column(unique=True)


class MealEntry(Base):
    """Приём пищи пользователя за конкретный день."""

    add_actions_author = False

    user_id: Mapped[UUID] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"), index=True)
    date: Mapped[date]
    meal_type: Mapped[MealTypeEnum] = mapped_column(make_enum_column_type(MealTypeEnum))
    notes: Mapped[str | None]
    source: Mapped[MealSourceEnum] = mapped_column(make_enum_column_type(MealSourceEnum), default=MealSourceEnum.manual)
    photo_url: Mapped[str | None]

    user: Mapped["User"] = relationship("User")
    items: Mapped[list["MealFoodItem"]] = relationship("MealFoodItem", cascade="all, delete-orphan")


class MealFoodItem(Base):
    """Продукт в составе приёма пищи с зафиксированным КБЖУ."""

    add_actions_author = False

    meal_entry_id: Mapped[UUID] = mapped_column(ForeignKey("meal_entry.id", ondelete="CASCADE"), index=True)
    food_item_id: Mapped[UUID | None] = mapped_column(ForeignKey("food_item.id", ondelete="SET NULL"), index=True)
    custom_name: Mapped[str | None]
    amount_g: Mapped[float]
    calories_kcal: Mapped[float]
    protein_g: Mapped[float]
    fat_g: Mapped[float]
    carbs_g: Mapped[float]

    meal_entry: Mapped["MealEntry"] = relationship("MealEntry", back_populates="items")
    food_item: Mapped[Optional["FoodItem"]] = relationship("FoodItem")
