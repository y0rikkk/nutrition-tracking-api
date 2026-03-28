"""User Pydantic schemas."""

from dataclasses import dataclass
from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from nutrition_tracking_api.api.schemas.auth.roles import RoleOut
from nutrition_tracking_api.api.schemas.filters import BasePaginationFilter


class UserCreate(BaseModel):
    """Schema for creating a user."""

    username: str
    password: Annotated[
        str | None, Field(exclude=True)
    ] = None  # plain-text, хешируется в _handle_pre_create; в model_dump не попадает
    password_hash: str | None = None  # хеш пароля, записывается в БД
    access_token: str | None = None
    is_superuser: bool = False
    is_service_user: bool = False
    email: str | None = None
    access_token_expires_at: datetime | None = None
    ad_login: str | None = None
    master_id: int | None = None
    full_name: str | None = None


class UserUpdate(BaseModel):
    """Schema for updating a user."""

    model_config = ConfigDict(extra="forbid")

    username: str | None = None
    access_token: str | None = None
    access_token_expires_at: datetime | None = None
    is_superuser: bool | None = None
    is_service_user: bool | None = None
    email: str | None = None
    ad_login: str | None = None
    master_id: int | None = None
    full_name: str | None = None


class UserOut(BaseModel):
    """Schema for user output."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    access_token: str | None
    access_token_expires_at: datetime | None
    is_superuser: bool
    is_service_user: bool
    email: str | None
    ad_login: str | None
    master_id: int | None
    full_name: str | None
    roles: list[RoleOut]
    role_ids: list[UUID]
    created_at: datetime
    updated_at: datetime


class UserOutMulti(BaseModel):
    """Schema for user list output."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    ad_login: str | None
    master_id: int | None
    full_name: str | None
    email: str | None = None
    roles: list[RoleOut]
    role_ids: list[UUID]
    created_at: datetime
    updated_at: datetime


class UserRoutePermissions(BaseModel):
    id: UUID
    username: str
    access_token: str | None
    access_token_expires_at: datetime | None
    is_service_user: bool
    is_superuser: bool
    ad_login: str | None
    full_name: str | None
    master_id: int | None

    permissions: dict[str, dict[str, Any]] | None = None

    model_config = ConfigDict(from_attributes=True)


@dataclass
class UserFilters(BasePaginationFilter):
    """Фильтры для пользователей."""

    username__ilike: str | None = None
    email__ilike: str | None = None
    ad_login__ilike: str | None = None
    is_superuser: bool | None = None
    is_service_user: bool | None = None
    master_id: int | None = None
    role_id: UUID | None = None
    role_name__ilike: str | None = None
