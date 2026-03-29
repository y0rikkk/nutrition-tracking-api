"""Auth ORM models."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Column, DateTime, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.associationproxy import AssociationProxy, association_proxy
from sqlalchemy.orm import Mapped, mapped_column, relationship

from nutrition_tracking_api.orm.models.base import Base


class UserRoles(Base):
    """Связующая таблица User ↔ Role (M2M)."""

    add_actions_author = False

    __table_args__ = (UniqueConstraint("user_id", "role_id", name="_unique_user_role"),)

    user_id: Mapped[UUID] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"), index=True)
    role_id: Mapped[UUID] = mapped_column(ForeignKey("role.id"), index=True)


class RolePolicy(Base):
    """Связующая таблица Role ↔ Policy (M2M)."""

    add_actions_author = False

    __table_args__ = (UniqueConstraint("policy_id", "role_id", name="_unique_policy_role"),)

    policy_id: Mapped[UUID] = mapped_column(ForeignKey("policy.id"))
    role_id: Mapped[UUID] = mapped_column(ForeignKey("role.id", ondelete="CASCADE"))


class Role(Base):
    """Роль пользователя."""

    __table_args__ = (
        Index(
            "ix_unique_default",
            "is_default",
            unique=True,
            postgresql_where=Column("is_default") == True,  # noqa: E712
        ),
    )

    name: Mapped[str] = mapped_column(unique=True)
    description: Mapped[str | None] = mapped_column(postgresql.TEXT, nullable=True)
    is_default: Mapped[bool] = mapped_column(nullable=False, default=False)

    users: Mapped[list["User"]] = relationship("User", secondary="user_roles", viewonly=True)
    policies: Mapped[list["Policy"]] = relationship("Policy", secondary="role_policy", viewonly=True)

    _role_policies: Mapped[list[RolePolicy]] = relationship("RolePolicy", cascade="all, delete-orphan")
    policy_ids: AssociationProxy[list[UUID]] = association_proxy(
        "_role_policies",
        "policy_id",
        creator=lambda policy_id: RolePolicy(policy_id=policy_id),
    )


class Policy(Base):
    """Политика доступа."""

    name: Mapped[str] = mapped_column(unique=True)
    description: Mapped[str | None] = mapped_column(postgresql.TEXT, nullable=True)

    roles: Mapped[list["Role"]] = relationship("Role", secondary="role_policy", viewonly=True)

    targets: Mapped[list[str]] = mapped_column(postgresql.JSONB)
    actions: Mapped[list[str]] = mapped_column(postgresql.JSONB)
    matchers: Mapped[list[dict[str, Any]] | None] = mapped_column(postgresql.JSONB, nullable=True)
    options: Mapped[list[str] | None] = mapped_column(postgresql.JSONB, nullable=True)


class User(Base):
    """Пользователь системы."""

    add_actions_author = False

    email: Mapped[str | None]
    username: Mapped[str] = mapped_column(unique=True)
    password_hash: Mapped[str | None] = mapped_column(nullable=True)
    access_token: Mapped[str | None] = mapped_column(unique=True, nullable=True)
    access_token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_superuser: Mapped[bool]
    is_service_user: Mapped[bool]
    full_name: Mapped[str | None]

    roles: Mapped[list["Role"]] = relationship("Role", secondary="user_roles", viewonly=True)

    _user_roles: Mapped[list[UserRoles]] = relationship("UserRoles", cascade="all, delete-orphan")
    role_ids: AssociationProxy[list[UUID]] = association_proxy(
        "_user_roles",
        "role_id",
        creator=lambda role_id: UserRoles(role_id=role_id),
    )
