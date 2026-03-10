"""Схемы для ролей."""

from dataclasses import dataclass
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from nutrition_tracking_api.api.schemas.auth.common import UserShortOut
from nutrition_tracking_api.api.schemas.auth.policies import PolicyOut
from nutrition_tracking_api.api.schemas.filters import BasePaginationFilter


class RoleCreate(BaseModel):
    """Схема для создания роли."""

    name: str
    description: str
    is_default: bool = False


class RoleUpdate(BaseModel):
    """Схема для обновления роли."""

    name: str | None = None
    description: str | None = None
    is_default: bool | None = None


class RoleOut(BaseModel):
    """Схема для вывода роли."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    is_default: bool
    policies: list[PolicyOut]
    policy_ids: list[UUID]
    creator: UserShortOut | None
    modifier: UserShortOut | None


@dataclass
class RoleFilters(BasePaginationFilter):
    """Фильтры для ролей."""

    name__ilike: str | None = None
    is_default: bool | None = None
    policy_id: UUID | None = None
