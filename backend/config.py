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

    # Security
    secret_key: str = Field(
        ...,
        description="Secret key for JWT tokens",
        alias="SECRET_KEY",
    )
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(default=30, description="Access token expiration in minutes")

    # Database
    database_url: str = Field(
        ...,
        description="PostgreSQL database connection URL",
        alias="DATABASE_URL",
    )

    # LLM Provider
    llm_base_url: str = Field(
        default="http://localhost:11434",
        description="Base URL for LLM provider (e.g., Ollama)",
        alias="LLM_BASE_URL",
    )
    ollama_model: str = Field(
        default="qwen3vl:4b",
        description="Ollama model name to use",
        alias="OLLAMA_MODEL",
    )
    openai_api_key: str | None = Field(
        default=None,
        description="OpenAI API key",
        alias="OPENAI_API_KEY",
    )
    openai_chat_model_id: str | None = Field(
        default="gpt-3.5-turbo-instruct",
        description="OpenAI chat model ID (e.g., gpt-4, gpt-3.5-turbo)",
        alias="OPENAI_CHAT_MODEL_ID",
    )

    # Generation
    serve_actual_generation: bool = Field(
        default=False,
        description="If True, use actual LLM generation. If False, return dummy values for frontend development",
        alias="SERVE_ACTUAL_GENERATION",
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
