"""Схемы для пагинированных ответов."""

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    """
    Пагинированный ответ.

    Attributes
    ----------
        items: Список элементов на текущей странице
        count: Общее количество элементов

    """

    items: list[T]
    count: int
