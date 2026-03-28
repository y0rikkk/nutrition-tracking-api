"""Refresh token ORM model."""


from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from nutrition_tracking_api.orm.models.auth import User
from nutrition_tracking_api.orm.models.base import Base


class RefreshToken(Base):
    """Refresh токен пользователя (хранится для возможности отзыва)."""

    add_actions_author = False

    user_id: Mapped[UUID] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"), index=True)
    jti: Mapped[str] = mapped_column(String, unique=True, index=True)  # JWT ID — уникальный ID токена
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False)

    user: Mapped[User] = relationship("User", foreign_keys=[user_id])
