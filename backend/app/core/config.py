"""Validated backend configuration."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables or a local .env file."""

    app_name: str = "SAHYOG Backend"
    environment: str = "development"
    database_url: str = Field(
        default="postgresql+psycopg://sahyog:sahyog@localhost:5432/sahyog",
        repr=False,
    )
    sql_echo: bool = False
    auth_secret_key: str = Field(default="", repr=False)
    auth_issuer: str = "sahyog-backend"
    access_token_expire_minutes: int = 30
    verification_timeout_seconds: int = 15
    detector_baseline_mean_bpm: float = 72.0
    detector_baseline_std_bpm: float = 4.0
    detector_session_cache_size: int = 256

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="SAHYOG_",
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
