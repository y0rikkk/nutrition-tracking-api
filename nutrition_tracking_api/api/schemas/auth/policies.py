"""Схемы для политик доступа."""

from dataclasses import dataclass
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from nutrition_tracking_api.api.schemas.auth.common import MatcherRule, UserShortOut
from nutrition_tracking_api.api.schemas.filters import BasePaginationFilter


class PolicyCreate(BaseModel):
    """Схема для создания политики."""

    name: str
    description: str
    targets: list[str]
    actions: list[str]
    options: list[str] | None = None
    matchers: list[MatcherRule] | None = None


class PolicyUpdate(BaseModel):
    """Схема для обновления политики."""

    name: str | None = None
    description: str | None = None
    targets: list[str] | None = None
    actions: list[str] | None = None
    options: list[str] | None = None
    matchers: list[MatcherRule] | None = None


class PolicyOut(BaseModel):
    """Схема для вывода политики."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    targets: list[str]
    actions: list[str]
    options: list[str] | None
    matchers: list[MatcherRule] | None
    creator: UserShortOut | None
    modifier: UserShortOut | None


@dataclass
class PolicyFilters(BasePaginationFilter):
    """Фильтры для политик."""

    name__ilike: str | None = None
    target__ilike: str | None = None
    action__ilike: str | None = None
    option__ilike: str | None = None
