"""Application settings."""

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    CORS_ORIGINS: str = "*"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    APP_NAME: str = "nutrition_tracking_api"
    ENV: Literal["dev", "prod"] = "dev"
    DEBUG: bool = True

    # Database
    POSTGRES_HOST: str = ""
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = ""
    POSTGRES_PASSWORD: str = ""
    POSTGRES_DB: str = ""
    POSTGRES_SCHEMA: str | None = None

    @property
    def database_url(self) -> str:
        """Construct database URL."""
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    test_database_url: str = "postgresql://postgres:password@localhost:5432/nutrition_tracking_api_test"

    # Logging
    LOG_LEVEL: str = "INFO"

    # Auth / JWT settings
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Admin seed
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str


settings = Settings()
