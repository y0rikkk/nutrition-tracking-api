"""Утилиты для ORM моделей."""

import enum

from sqlalchemy import Enum as SAEnum


def make_enum_column_type(enum_cls: type[enum.StrEnum]) -> SAEnum:
    """Создать тип колонки для StrEnum без native PostgreSQL ENUM типа.

    Использует VARCHAR с CHECK constraint вместо native PostgreSQL ENUM,
    что позволяет не создавать миграции при изменении набора значений в enum.
    """
    return SAEnum(
        enum_cls,
        native_enum=False,
        length=50,
        values_callable=lambda x: [i.value for i in x],
    )
