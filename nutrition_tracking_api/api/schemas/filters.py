"""Базовые классы для фильтрации."""

from dataclasses import dataclass
from typing import Any


@dataclass
class BaseFilter:
    """Базовый класс для фильтров без пагинации."""

    def model_dump(self, exclude: set[str] | None = None) -> dict[str, Any]:
        if exclude is not None:
            return {key: val for key, val in self.__dict__.items() if val is not None and key not in exclude}
        return {key: val for key, val in self.__dict__.items() if val is not None}


@dataclass
class BasePaginationFilter(BaseFilter):
    """
    Базовый класс для фильтрации с пагинацией и сортировкой.

    Attributes
    ----------
        limit: Максимальное количество элементов (по умолчанию 1000)
        offset: Смещение для пагинации (по умолчанию 0)
        order_by: Поле для сортировки (по умолчанию None - сортировка по created_at)
        desc: Обратная сортировка (по умолчанию False - сортировка по возрастанию)

    """

    limit: int = 1000
    offset: int = 0
    order_by: str | None = None
    desc: bool = False


@dataclass
class DeleteParameter:
    """
    Параметры для операции удаления.

    Attributes
    ----------
        force: Принудительное удаление (физическое удаление вместо soft delete)

    """

    force: bool = False
