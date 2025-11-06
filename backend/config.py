"""Application configuration using Pydantic Settings."""

from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# Calculate project root: config.py is in backend/, so go up one level
_CONFIG_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _CONFIG_DIR.parent


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=str(_PROJECT_ROOT / "backend" / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = Field(default="Marketing Copilot", description="Application name")
    app_env: str = Field(default="development", description="Application environment")

    # Database
    database_url: str = Field(
        ...,
        description="PostgreSQL database connection URL",
        alias="DATABASE_URL",
    )

    @field_validator("database_url", mode="before")
    @classmethod
    def validate_database_url(cls, v: str | None) -> str:
        """Validate and normalize database URL."""
        if v is None or v == "":
            raise ValueError("DATABASE_URL is required")
        return v.strip()

    @field_validator("app_env", mode="before")
    @classmethod
    def normalize_app_env(cls, v: str) -> str:
        """Normalize app environment to lowercase."""
        if isinstance(v, str):
            return v.lower().strip()

    @field_validator("app_name", mode="before")
    @classmethod
    def normalize_app_name(cls, v: str) -> str:
        """Normalize app name by stripping whitespace."""
        if isinstance(v, str):
            return v.strip()


def get_settings() -> Settings:
    """Get application settings instance.

    Returns:
        Settings: Application settings instance

    Example:
        ```python
        from backend.config import get_settings

        settings = get_settings()
        print(settings.database_url)
        ```
    """
    return Settings()


# Global settings instance
settings = get_settings()
