"""Core ORM models."""

from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column, relationship

from nutrition_tracking_api.orm.choices.history import HistoryActionEnum
from nutrition_tracking_api.orm.models.base import Base

if TYPE_CHECKING:
    from nutrition_tracking_api.orm.models.auth import User


class History(Base):
    """Audit log table for tracking entity changes."""

    add_actions_author = False

    object_type: Mapped[str] = mapped_column(String(255))
    object_id: Mapped[UUID | None] = mapped_column(nullable=True, index=True)
    user_id: Mapped[UUID | None] = mapped_column(ForeignKey("user.id", ondelete="SET NULL"), nullable=True)
    user: Mapped["User | None"] = relationship("User", lazy="noload")
    parent_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    parent_type: Mapped[str] = mapped_column(String(255), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(postgresql.JSONB)
    action: Mapped[HistoryActionEnum] = mapped_column(
        Enum(HistoryActionEnum, name="historyactionenum", values_callable=lambda x: [e.value for e in x])
    )
    request_id: Mapped[UUID | None] = mapped_column(nullable=True)
