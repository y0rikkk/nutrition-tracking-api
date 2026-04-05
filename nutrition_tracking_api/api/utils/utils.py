"""Вспомогательные утилиты для API."""

from datetime import date
from enum import Enum
from typing import Any
from uuid import UUID

from sqlalchemy.ext.associationproxy import _AssociationList
from sqlalchemy.orm import class_mapper

from nutrition_tracking_api.orm.models.base import Base


def dump_model_field(value: Any) -> Any:
    """Конвертировать значение поля в JSON-сериализуемый тип."""
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, list | _AssociationList):
        return [str(item) for item in value]
    return value


def dump_model(
    data: Base,
    include_fields: list[str] | None = None,
) -> dict[str, Any]:
    """
    Сериализовать SQLAlchemy модель в словарь.

    Исключает поля: updated_at, access_token, archived_at.

    Args:
    ----
        data: SQLAlchemy модель
        include_fields: Дополнительные поля (атрибуты класса, не колонки)

    Returns:
    -------
        dict: Словарь с данными модели

    """
    dump: dict[str, Any] = {}
    mapper = class_mapper(data.__class__)
    if include_fields:
        for attr_name in dir(data.__class__):
            if attr_name in include_fields:
                dump[attr_name] = dump_model_field(getattr(data, attr_name, None))
    for column in mapper.columns:
        if column.name in ["updated_at", "access_token", "archived_at"]:
            continue
        dump[column.name] = dump_model_field(getattr(data, column.name, None))
    return dump
