"""Database configuration and session management (sync SQLAlchemy)."""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from nutrition_tracking_api.settings import settings

# Create sync engine
engine = create_engine(
    settings.database_url,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

# Create session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def check_db_health() -> bool:
    """
    Check database connection health.

    Returns
    -------
        bool: True if database is healthy, False otherwise.

    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001
        return False
    else:
        return True
