"""History schemas."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, computed_field

from nutrition_tracking_api.api.schemas.auth.common import UserShortOut
from nutrition_tracking_api.api.schemas.filters import BasePaginationFilter
from nutrition_tracking_api.orm.choices.history import HistoryActionEnum


class HistoryDiff(BaseModel):
    """
    Разница между старым и новым состоянием сущности.

    Пример:
        old_obj: {status: 'pending', amount: 10}
        new_obj: {status: 'done', amount: 10}
        diff_obj: {status: 'done'}  ← только изменённые поля
    """

    old_obj: dict[str, Any] | None = None
    new_obj: dict[str, Any] | None = None
    extra_fields: dict[str, Any] | None = None

    @computed_field
    def diff_obj(self) -> dict[str, Any] | None:
        if self.old_obj and self.new_obj:
            return {
                attr_name: self.new_obj[attr_name]
                for attr_name in self.new_obj
                if attr_name not in self.old_obj or self.new_obj[attr_name] != self.old_obj[attr_name]
            }
        return self.new_obj


class HistoryCreate(BaseModel):
    """Схема для создания записи истории."""

    object_type: str
    object_id: UUID | None = None
    payload: HistoryDiff
    user_id: UUID | None = None
    parent_id: UUID
    parent_type: str
    request_id: UUID | None = None

    @computed_field
    def action(self) -> HistoryActionEnum:
        """Определяет тип действия автоматически из diff."""
        if self.payload.old_obj and self.payload.new_obj:
            if (
                "is_archive" in self.payload.new_obj
                and "is_archive" in self.payload.old_obj
                and self.payload.new_obj["is_archive"] != self.payload.old_obj["is_archive"]
            ):
                return HistoryActionEnum.ARCHIVE if self.payload.new_obj["is_archive"] else HistoryActionEnum.RECOVER
            return HistoryActionEnum.UPDATE
        if self.payload.old_obj:
            return HistoryActionEnum.DELETE
        return HistoryActionEnum.CREATE


class HistoryOut(BaseModel):
    """Схема для вывода записи истории."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    object_type: str
    object_id: UUID | None = None
    action: HistoryActionEnum
    payload: HistoryDiff
    user_id: UUID | None = None
    user: UserShortOut | None = None
    parent_id: UUID
    parent_type: str
    request_id: UUID | None = None


@dataclass
class HistoryFilter(BasePaginationFilter):
    """Фильтры для записей истории."""

    object_type__eq: str | None = None
    object_id__eq: UUID | None = None
    user_id__eq: UUID | None = None
    parent_id__eq: UUID | None = None
    parent_type__eq: str | None = None
    action__eq: HistoryActionEnum | None = None
