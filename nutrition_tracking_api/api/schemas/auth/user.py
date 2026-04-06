"""User Pydantic schemas."""

import datetime as dt
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from nutrition_tracking_api.api.schemas.auth.roles import RoleOut
from nutrition_tracking_api.api.schemas.filters import BasePaginationFilter


class GenderEnum(StrEnum):
    """Пол пользователя."""

    male = "male"
    female = "female"


class ActivityLevelEnum(StrEnum):
    """Уровень физической активности."""

    sedentary = "sedentary"
    lightly_active = "lightly_active"
    moderately_active = "moderately_active"
    very_active = "very_active"
    extra_active = "extra_active"


class UserProfileUpdate(BaseModel):
    """Схема для обновления профиля текущего пользователя."""

    model_config = ConfigDict(extra="forbid")

    birth_date: dt.date | None = None
    gender: GenderEnum | None = None
    height_cm: float | None = Field(None, gt=0, le=300)
    weight_kg: float | None = Field(None, gt=0, le=700)
    activity_level: ActivityLevelEnum | None = None


class UserCreate(BaseModel):
    """Schema for creating a user."""

    username: str
    password: Annotated[
        str | None, Field(exclude=True)
    ] = None  # plain-text, хешируется в _handle_pre_create; в model_dump не попадает
    password_hash: str | None = None  # хеш пароля, записывается в БД
    is_superuser: bool = False
    email: str | None = None
    full_name: str | None = None
    birth_date: dt.date
    gender: GenderEnum
    height_cm: float = Field(gt=0, le=300)
    weight_kg: float = Field(gt=0, le=700)
    activity_level: ActivityLevelEnum


class UserUpdate(UserProfileUpdate):
    """Schema for updating a user (admin)."""

    username: str | None = None
    is_superuser: bool | None = None
    email: str | None = None
    full_name: str | None = None


class UserOut(BaseModel):
    """Schema for user output."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    is_superuser: bool
    email: str | None
    full_name: str | None
    birth_date: dt.date
    gender: GenderEnum
    height_cm: float
    weight_kg: float
    activity_level: ActivityLevelEnum
    roles: list[RoleOut]
    role_ids: list[UUID]
    created_at: datetime
    updated_at: datetime


class UserOutMulti(BaseModel):
    """Schema for user list output."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    full_name: str | None
    email: str | None = None
    roles: list[RoleOut]
    role_ids: list[UUID]
    created_at: datetime
    updated_at: datetime


@dataclass
class UserFilters(BasePaginationFilter):
    """Фильтры для пользователей."""

    username__ilike: str | None = None
    email__ilike: str | None = None
    is_superuser: bool | None = None
    role_id: UUID | None = None
    role_name__ilike: str | None = None
