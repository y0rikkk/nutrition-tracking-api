"""History action enum."""

from enum import StrEnum


class HistoryActionEnum(StrEnum):
    CREATE = "create"
    UPDATE = "update"
    ARCHIVE = "archive"  # soft delete: is_archive False → True
    RECOVER = "recover"  # восстановление: is_archive True → False
    DELETE = "delete"  # hard delete
