"""Unit tests for Recommendation Agent."""

import pytest
from google.adk.agents import InvocationContext, LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.sessions import Session

from src.venue_recommendation_agent.recommendation_agent import (
    auto_save_to_memory,
    create_recommendation_agent,
)


class TestRecommendationAgent:
    """Test suite for recommendation_agent.py functionality."""

    def test_create_recommendation_agent_returns_llm_agent(self):
        """Test create_recommendation_agent returns properly configured LlmAgent."""
        # When: Recommendation agent is created
        agent = create_recommendation_agent()

        # Then: Should return LlmAgent with correct properties
        assert isinstance(agent, LlmAgent)
        assert agent.name == "recommendation_agent"

    def test_create_recommendation_agent_logs_creation(self, caplog):
        """Test create_recommendation_agent logs agent creation."""
        # When: Recommendation agent is created
        with caplog.at_level("INFO"):
            create_recommendation_agent()

        # Then: Should log creation messages
        assert "Creating Recommendation Agent" in caplog.text
        assert "Recommendation Agent created successfully" in caplog.text

    def test_recommendation_agent_uses_higher_temperature(self):
        """Test recommendation agent uses higher temperature for creativity."""
        # When: Recommendation agent is created
        agent = create_recommendation_agent()

        # Then: Should use higher temperature for creative recommendations
        assert agent.generate_content_config.temperature == 0.7
        assert agent.generate_content_config.top_p == 0.95
        assert agent.generate_content_config.max_output_tokens == 2048

    def test_recommendation_agent_configures_retry_options(self):
        """Test recommendation agent configures Google API retry options."""
        # When: Recommendation agent is created
        agent = create_recommendation_agent()

        # Then: Should have retry configuration
        http_options = agent.generate_content_config.http_options
        assert http_options is not None
        assert http_options.retry_options is not None
        assert http_options.retry_options.attempts == 3
        assert http_options.retry_options.initial_delay == 1.0
        assert http_options.retry_options.max_delay == 10.0
        assert 429 in http_options.retry_options.http_status_codes
        assert 500 in http_options.retry_options.http_status_codes

    def test_recommendation_agent_uses_custom_model(self, mocker):
        """Test recommendation agent uses custom Gemini model from settings."""
        # Given: Custom model in settings
        mocker.patch(
            "src.venue_recommendation_agent.recommendation_agent.settings.gemini_model",
            "gemini-2.5-flash-lite",
        )

        # When: Recommendation agent is created
        agent = create_recommendation_agent()

        # Then: Should use custom model
        assert agent.model == "gemini-2.5-flash-lite"

    def test_recommendation_agent_accepts_tools(self, mocker):
        """Test create_recommendation_agent accepts tools parameter."""
        # Given: Mock tools
        mock_tool1 = mocker.Mock()
        mock_tool2 = mocker.Mock()

        # When: Agent is created with tools
        agent = create_recommendation_agent(tools=[mock_tool1, mock_tool2])

        # Then: Should have the tools
        assert mock_tool1 in agent.tools
        assert mock_tool2 in agent.tools
        assert len(agent.tools) == 2

    def test_recommendation_agent_without_tools(self):
        """Test create_recommendation_agent works without tools."""
        # When: Agent is created without tools
        agent = create_recommendation_agent()

        # Then: Should have empty tools list
        assert agent.tools == []

    def test_recommendation_agent_with_none_tools(self):
        """Test create_recommendation_agent with None tools defaults to empty list."""
        # When: Agent is created with None tools
        agent = create_recommendation_agent(tools=None)

        # Then: Should have empty tools list
        assert agent.tools == []

    def test_recommendation_agent_has_memory_callback(self):
        """Test recommendation agent has auto_save_to_memory callback configured."""
        # When: Recommendation agent is created
        agent = create_recommendation_agent()

        # Then: Should have the memory callback
        assert agent.after_agent_callback == auto_save_to_memory


class TestAutoSaveToMemory:
    """Test suite for auto_save_to_memory callback."""

    @pytest.fixture
    def mock_callback_context(self, mocker, mock_memory_service):
        """Create a mock CallbackContext with memory support."""
        mock_context = mocker.Mock(spec=CallbackContext)
        mock_context.add_session_to_memory = mocker.AsyncMock()

        # Mock the _invocation_context.session for logging
        mock_session = mocker.Mock(spec=Session)
        mock_session.app_name = "test_app"
        mock_session.user_id = "test_user"
        mock_session.id = "test_session_id"

        mock_invocation_context = mocker.Mock(spec=InvocationContext)
        mock_invocation_context.session = mock_session
        mock_invocation_context.memory_service = mock_memory_service

        mock_context._invocation_context = mock_invocation_context
        return mock_context

    async def test_auto_save_to_memory_calls_add_session_to_memory(
        self, mock_callback_context
    ):
        """Test callback successfully saves session to memory."""
        # When: Callback is invoked
        await auto_save_to_memory(mock_callback_context)

        # Then: Should call add_session_to_memory
        mock_callback_context.add_session_to_memory.assert_called_once()

    async def test_auto_save_to_memory_logs_success(
        self, mock_callback_context, caplog
    ):
        """Test callback logs success message."""
        # When: Callback is invoked
        with caplog.at_level("INFO"):
            await auto_save_to_memory(mock_callback_context)

        # Then: Should log success
        assert "Session saved to memory successfully" in caplog.text

    async def test_auto_save_to_memory_handles_value_error(
        self, mock_callback_context, caplog
    ):
        """Test callback handles missing memory service gracefully."""
        # Given: Callback context where add_session_to_memory raises ValueError
        mock_callback_context.add_session_to_memory.side_effect = ValueError(
            "memory service is not available"
        )

        # When: Callback is invoked
        with caplog.at_level("WARNING"):
            await auto_save_to_memory(mock_callback_context)

        # Then: Should log warning, not raise
        assert "Could not save to memory" in caplog.text
