"""Unit tests for configuration management."""

import os

import pytest
from pydantic import ValidationError

from src.config import Settings


class TestSettings:
    """Test suite for Settings configuration."""

    def test_settings_with_valid_api_keys(self, mocker):
        """Test Settings initialization with valid API keys."""
        # Given: Valid environment variables
        mocker.patch.dict(
            "os.environ",
            {
                "YELP_API_KEY": "valid_yelp_key_123",
                "GOOGLE_API_KEY": "valid_google_key_456",
                "GEMINI_MODEL": "gemini-2.5-flash-lite",
                "LOG_LEVEL": "INFO",
            },
        )

        # When: Settings is instantiated
        settings = Settings()

        # Then: Settings should be configured correctly
        assert settings.yelp_api_key == "valid_yelp_key_123"
        assert settings.google_api_key == "valid_google_key_456"
        assert settings.gemini_model == "gemini-2.5-flash-lite"
        assert settings.log_level == "INFO"

    def test_settings_rejects_placeholder_yelp_key(self, mocker):
        """Test Settings rejects placeholder Yelp API key."""
        # Given: Placeholder Yelp API key
        mocker.patch.dict(
            "os.environ",
            {
                "YELP_API_KEY": "your_yelp_api_key",
                "GOOGLE_API_KEY": "valid_google_key_456",
            },
        )

        # When: Settings is instantiated
        # Then: ValidationError should be raised
        with pytest.raises(
            ValidationError, match="API key must be set to a valid value"
        ):
            Settings()

    def test_settings_rejects_placeholder_google_key(self, mocker):
        """Test Settings rejects placeholder Google API key."""
        # Given: Placeholder Google API key
        mocker.patch.dict(
            "os.environ",
            {
                "YELP_API_KEY": "valid_yelp_key_123",
                "GOOGLE_API_KEY": "your_google_api_key",
            },
        )

        # When: Settings is instantiated
        # Then: ValidationError should be raised
        with pytest.raises(
            ValidationError,
            match="API key must be set to a valid value, not a placeholder",
        ):
            Settings()

    def test_settings_allows_none_google_api_key(self, mocker):
        """Test Settings allows None for Google API key (uses ADC)."""
        # Given: Explicitly set GOOGLE_API_KEY to empty (will use ADC)
        mocker.patch.dict(
            "os.environ",
            {
                "YELP_API_KEY": "valid_yelp_key_123",
                "GOOGLE_API_KEY": "",  # Explicitly empty - will use ADC
            },
        )

        # When: Settings is instantiated
        settings = Settings()

        # Then: google_api_key should be None or empty
        assert settings.yelp_api_key == "valid_yelp_key_123"
        # Empty string is allowed for ADC usage
        assert settings.google_api_key == ""
        assert settings.gemini_model == "gemini-2.5-flash-lite"

    def test_settings_allows_empty_string_google_api_key(self, mocker):
        """Test Settings allows empty string for Google API key (uses ADC)."""
        # Given: Empty Google API key
        mocker.patch.dict(
            "os.environ",
            {
                "YELP_API_KEY": "valid_yelp_key_123",
                "GOOGLE_API_KEY": "",
            },
        )

        # When: Settings is instantiated
        settings = Settings()

        # Then: google_api_key should be None or empty
        assert settings.yelp_api_key == "valid_yelp_key_123"
        # Empty string gets converted to None by Pydantic
        assert settings.google_api_key == ""

    def test_settings_rejects_empty_api_key(self, mocker):
        """Test Settings rejects empty API keys."""
        # Given: Empty Yelp API key
        mocker.patch.dict(
            "os.environ",
            {
                "YELP_API_KEY": "",
                "GOOGLE_API_KEY": "valid_google_key_456",
            },
        )

        # When: Settings is instantiated
        # Then: ValidationError should be raised
        with pytest.raises(
            ValidationError, match="API key must be set to a valid value"
        ):
            Settings()

    def test_settings_default_values(self, mocker):
        """Test Settings applies default values correctly."""
        # Given: Only required API keys are set
        mocker.patch.dict(
            "os.environ",
            {
                "YELP_API_KEY": "valid_yelp_key_123",
                "GOOGLE_API_KEY": "valid_google_key_456",
            },
            clear=True,
        )

        # When: Settings is instantiated
        settings = Settings()

        # Then: Default values should be applied
        assert settings.gemini_model == "gemini-2.5-flash-lite"
        assert settings.log_level == "INFO"

    def test_settings_validates_log_level(self, mocker):
        """Test Settings validates log level."""
        # Given: Invalid log level
        mocker.patch.dict(
            "os.environ",
            {
                "YELP_API_KEY": "valid_yelp_key_123",
                "GOOGLE_API_KEY": "valid_google_key_456",
                "LOG_LEVEL": "INVALID",
            },
        )

        # When: Settings is instantiated
        # Then: ValidationError should be raised
        with pytest.raises(ValidationError, match="Log level must be one of"):
            Settings()

    def test_settings_normalises_log_level_case(self, mocker):
        """Test Settings normalises log level to uppercase."""
        # Given: Lowercase log level
        mocker.patch.dict(
            "os.environ",
            {
                "YELP_API_KEY": "valid_yelp_key_123",
                "GOOGLE_API_KEY": "valid_google_key_456",
                "LOG_LEVEL": "debug",
            },
        )

        # When: Settings is instantiated
        settings = Settings()

        # Then: Log level should be uppercased
        assert settings.log_level == "DEBUG"

    def test_settings_configures_vertex_ai_env_vars(self, mocker):
        """Test Settings configures Vertex AI environment variables when no API key."""
        # Given: No Google API key, use Vertex AI
        mocker.patch.dict(
            "os.environ",
            {
                "YELP_API_KEY": "valid_yelp_key_123",
                "GOOGLE_API_KEY": "",
                "VERTEX_PROJECT": "my-gcp-project",
                "VERTEX_LOCATION": "europe-west1",
            },
        )

        # When: Settings is instantiated
        Settings()

        # Then: Vertex AI environment variables should be set
        assert os.environ.get("GOOGLE_GENAI_USE_VERTEXAI") == "true"
        assert os.environ.get("GOOGLE_CLOUD_PROJECT") == "my-gcp-project"
        assert os.environ.get("GOOGLE_CLOUD_LOCATION") == "europe-west1"

    def test_settings_configures_api_key_env_var(self, mocker):
        """Test Settings configures Google API key environment variable."""
        # Given: Google API key provided
        mocker.patch.dict(
            "os.environ",
            {
                "YELP_API_KEY": "valid_yelp_key_123",
                "GOOGLE_API_KEY": "valid_google_key_456",
            },
        )

        # When: Settings is instantiated
        Settings()

        # Then: Google API key should be set and Vertex AI disabled
        assert os.environ.get("GOOGLE_API_KEY") == "valid_google_key_456"
        assert os.environ.get("GOOGLE_GENAI_USE_VERTEXAI") is None
