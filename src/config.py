"""Configuration management using Pydantic Settings."""

import os
from functools import lru_cache

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    # Yelp API Configuration
    yelp_api_key: str = Field(
        ..., description="Yelp API key from https://www.yelp.com/developers"
    )

    # Google Gemini Configuration
    google_api_key: str | None = Field(
        default=None,
        description="Google API key from https://aistudio.google.com/apikey. "
        "If not provided, will use Vertex AI with Application Default Credentials",
    )
    gemini_model: str = Field(
        default="gemini-2.5-flash-lite", description="Gemini model to use"
    )

    # Vertex AI Configuration (used when google_api_key is not provided)
    vertex_project: str | None = Field(
        default=None,
        description="Google Cloud project ID for Vertex AI. Required when using ADC without API key",
    )
    vertex_location: str = Field(
        default="europe-west1",
        description="Google Cloud region for Vertex AI",
    )

    # Development
    log_level: str = Field(default="INFO", description="Application log level")

    @field_validator("yelp_api_key")
    @classmethod
    def validate_yelp_api_key(cls, v: str) -> str:
        """Validate that Yelp API key is not empty or placeholder value."""
        if not v or v.startswith("your_"):
            raise ValueError("API key must be set to a valid value")
        return v

    @field_validator("google_api_key")
    @classmethod
    def validate_google_api_key(cls, v: str | None) -> str | None:
        """Validate that Google API key is not a placeholder value.

        None is allowed - will use Application Default Credentials instead.
        """
        if v and v.startswith("your_"):
            raise ValueError("API key must be set to a valid value, not a placeholder")
        return v

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is a valid option."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}")
        return v_upper

    @model_validator(mode="after")
    def configure_google_credentials(self) -> "Settings":
        """Configure Google credentials environment variables.

        If google_api_key is not provided, configures Vertex AI environment variables
        for Application Default Credentials.
        """
        if not self.google_api_key:
            # Use Vertex AI with Application Default Credentials
            os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "true"
            if self.vertex_project:
                os.environ["GOOGLE_CLOUD_PROJECT"] = self.vertex_project
            os.environ["GOOGLE_CLOUD_LOCATION"] = self.vertex_location
        else:
            # Use Google AI API with API key
            os.environ["GOOGLE_API_KEY"] = self.google_api_key
            # Ensure Vertex AI is not used
            os.environ.pop("GOOGLE_GENAI_USE_VERTEXAI", None)

        return self


@lru_cache()
def get_settings() -> Settings:
    """Get the application settings (cached singleton).

    Uses lru_cache to ensure only one Settings instance is created.
    This lazy initialization allows tests to import the module without
    requiring environment variables to be set.
    """
    return Settings()  # type: ignore[call-arg]


def __getattr__(name: str) -> Settings:
    """Lazy module attribute access for backwards compatibility.

    Allows 'from src.config import settings' to work without
    evaluating Settings() at import time.
    """
    if name == "settings":
        return get_settings()
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
