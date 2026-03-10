"""Базовый класс для всех ORM моделей."""

import re
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, MetaData
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    MappedColumn,
    declared_attr,
    mapped_column,
    relationship,
)
from sqlalchemy.util import hybridproperty

if TYPE_CHECKING:
    from nutrition_tracking_api.orm.models.auth import User

metadata = MetaData(
    naming_convention={
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    }
)


class Base(DeclarativeBase):
    """
    Базовый класс для всех ORM моделей.

    Автоматические поля:
    - id: UUID - Primary key (автогенерация uuid4)
    - created_at: datetime - Автоматически при создании
    - updated_at: datetime - Автоматически при обновлении
    - __tablename__ - Автоматическая генерация из CamelCase → snake_case
    - creator_id / modifier_id - FK на user.id (если add_actions_author=True)

    Ключевые свойства:
    - is_soft_deletable - True если модель является наследником ArchiveMixin

    Пример использования:
        class Purchase(ArchiveMixin, Base):  # Опционально: soft delete через ArchiveMixin
            name: Mapped[str] = mapped_column(unique=True)
            description: Mapped[str | None] = mapped_column(nullable=True)
    """

    metadata = metadata

    # Флаг для добавления полей автора создания/изменения
    add_actions_author = True

    @declared_attr  # type: ignore[arg-type]
    def __tablename__(cls) -> str:  # noqa: N805
        """Автоматическая генерация имени таблицы из CamelCase → snake_case."""
        return re.sub(r"(?<!^)(?=[A-Z])", "_", cls.__name__).lower()

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )
    created_at: Mapped[datetime] = mapped_column(
        default=datetime.now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        onupdate=datetime.now,
        default=datetime.now,
    )

    @hybridproperty
    def is_soft_deletable(cls) -> bool:  # noqa: N805
        """Проверяет наличие поля is_archive для soft delete функциональности."""
        return hasattr(cls, "is_archive")

    @declared_attr
    def creator_id(cls) -> MappedColumn[UUID | None]:  # noqa: N805
        if cls.add_actions_author:
            return mapped_column(ForeignKey("user.id", ondelete="SET NULL"), nullable=True)
        return None  # type: ignore[return-value]

    @declared_attr
    def creator(cls) -> "Mapped[User]":  # noqa: N805
        if cls.add_actions_author:
            return relationship("User", foreign_keys=[cls.creator_id], overlaps="archiver,modifier")  # type: ignore[list-item]
        return None  # type: ignore[return-value]

    @declared_attr
    def modifier_id(cls) -> MappedColumn[UUID | None]:  # noqa: N805
        if cls.add_actions_author:
            return mapped_column(ForeignKey("user.id", ondelete="SET NULL"), nullable=True)
        return None  # type: ignore[return-value]

    @declared_attr
    def modifier(cls) -> "Mapped[User]":  # noqa: N805
        if cls.add_actions_author:
            return relationship("User", foreign_keys=[cls.modifier_id], overlaps="archiver,creator")  # type: ignore[list-item]
        return None  # type: ignore[return-value]


class ArchiveMixin(Base):
    """
    Mixin для soft delete через поле is_archive.

    Поля:
    - is_archive: bool — признак архивации (False по умолчанию)
    - archived_at: datetime | None — дата архивации
    - archiver_id: UUID | None — FK на user.id (кто архивировал)
    - archiver: User — relationship на пользователя

    Пример использования:
        class SomeModel(ArchiveMixin, Base):
            name: Mapped[str] = mapped_column(unique=True)
    """

    __abstract__ = True

    is_archive: Mapped[bool] = mapped_column(default=False)
    archived_at: Mapped[datetime | None] = MappedColumn(DateTime(timezone=True), nullable=True)

    @declared_attr
    def archiver_id(cls) -> MappedColumn[UUID | None]:  # noqa: N805
        return mapped_column(ForeignKey("user.id", ondelete="SET NULL"), nullable=True)

    @declared_attr
    def archiver(cls) -> Mapped["User"]:  # noqa: N805
        return relationship("User", foreign_keys=[cls.archiver_id], overlaps="creator,modifier")  # type: ignore[list-item]
