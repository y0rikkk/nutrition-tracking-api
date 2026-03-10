"""Base factory for all model factories."""

from datetime import date
from uuid import uuid4

import factory
from factory.fuzzy import FuzzyDate
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, scoped_session, sessionmaker

from nutrition_tracking_api.settings import settings

# Создать engine для фабрик
engine = create_engine(
    settings.test_database_url,
    isolation_level="AUTOCOMMIT",
    pool_size=0,
)

# Session factory для фабрик
SessionFactory = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# Scoped session для factory-boy
s_session = scoped_session(SessionFactory)


def get_factory_session() -> Session:
    """
    Получить сессию для factory-boy.

    Используется в BaseSQLAlchemyModelFactory.Meta.sqlalchemy_session_factory
    """
    return s_session()


class BaseSQLAlchemyModelFactory(factory.alchemy.SQLAlchemyModelFactory):
    """
    Базовая фабрика для всех ORM моделей.

    Автоматически заполняет поля из Base:
    - id: UUID
    - created_at: datetime
    - updated_at: datetime
    """

    # Базовые поля из Base модели
    id = factory.LazyFunction(uuid4)
    created_at = FuzzyDate(date(2024, 1, 1))
    updated_at = FuzzyDate(date(2024, 1, 1))

    class Meta:
        abstract = True
        sqlalchemy_session_factory = get_factory_session
        sqlalchemy_session_persistence = factory.alchemy.SESSION_PERSISTENCE_COMMIT


class BaseMeta:
    """Базовая Meta конфигурация для фабрик."""

    sqlalchemy_session_factory = get_factory_session
    sqlalchemy_session_persistence = factory.alchemy.SESSION_PERSISTENCE_COMMIT
    strategy = "create"
