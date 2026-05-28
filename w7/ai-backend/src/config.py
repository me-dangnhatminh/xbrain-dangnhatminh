"""
Application configuration loaded from environment variables / .env file.
Uses pydantic-settings for validated, type-safe configuration (lazy init, testable).
"""

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    """All environment variables for DocHub AI Backend."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # AWS
    AWS_REGION: str

    # Bedrock
    BEDROCK_KB_ID: str
    BEDROCK_DS_ID: str
    BEDROCK_MODEL_ID: str

    # Cognito Authentication
    COGNITO_USER_POOL_ID: str
    COGNITO_CLIENT_ID: str

    # DynamoDB — optional, reserved for future conversation history
    DYNAMODB_TABLE: Optional[str] = None

    # Application
    APP_VERSION: str = "1.0.0"


@lru_cache(maxsize=1)
def get_config() -> Config:
    """Return the cached Config singleton (validated on first call)."""
    return Config()
