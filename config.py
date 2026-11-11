import sys
from functools import lru_cache
from typing import Any
from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Enterprise-grade application settings for Ask-Your-Payments backend.
    Enforces strict zero-trust validation and fail-fast startup behavior.
    """

    # --- PayPal Production/Sandbox Integration ---
    PAYPAL_CLIENT_ID: str = Field(
        ...,
        description="PayPal REST API OAuth 2.0 Client ID",
    )
    PAYPAL_CLIENT_SECRET: SecretStr = Field(
        ...,
        description="PayPal REST API OAuth 2.0 Client Secret (Masked)",
    )
    PAYPAL_WEBHOOK_ID: str = Field(
        ...,
        description="PayPal Webhook ID used for asymmetric signature verification",
    )

    # --- Persistence Layer ---
    DATABASE_URL: str = Field(
        ...,
        description="PostgreSQL connection string with database credentials (Masked)",
    )

    # --- AI & Intelligence Layer ---
    GEMINI_API_KEY: SecretStr = Field(
        ...,
        description="Google Gemini API Key for financial reconciliation reasoning (Masked)",
    )

    # Pydantic Settings Configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @field_validator(
        "PAYPAL_CLIENT_ID",
        "PAYPAL_CLIENT_SECRET",
        "PAYPAL_WEBHOOK_ID",
        "DATABASE_URL",
        "GEMINI_API_KEY",
        mode="before",
    )
    @classmethod
    def validate_non_empty(cls, v: Any, info) -> Any:
        """
        Guarantees that credentials are not empty strings or blank whitespace.
        """
        if v is None:
            raise ValueError(f"'{info.field_name}' is required and cannot be null.")
        if isinstance(v, str) and not v.strip():
            raise ValueError(
                f"'{info.field_name}' cannot be empty or contain only whitespace."
            )
        return v


@lru_cache
def get_settings() -> Settings:
    """
    Returns a cached singleton instance of validated settings.
    Fails fast with Pydantic ValidationError if any required environment variable is missing.
    """
    return Settings()


# Eager fail-fast instantiation at import time:
# Completely halts application boot before any server sockets or endpoints initialize.
try:
    settings = get_settings()
except Exception as exc:
    # Print formatted security alert to stderr and terminate startup
    sys.stderr.write(
        f"\n[CRITICAL SECURITY ALERT] Ask-Your-Payments Backend Failed to Boot!\n"
        f"Missing or invalid required environment variables:\n{exc}\n\n"
    )
    raise
