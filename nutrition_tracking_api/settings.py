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

    admin_token: str

    # Auth / JWT settings
    twork_api_endpoint: str = "https://twork.example.com"


settings = Settings()
