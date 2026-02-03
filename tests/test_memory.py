"""Unit tests for Memory functionality."""

import pytest
from google.adk.agents import InvocationContext
from google.adk.agents.callback_context import CallbackContext
from google.adk.sessions import Session
from google.adk.tools.preload_memory_tool import preload_memory_tool

from src.venue_recommendation_agent.agent import auto_save_to_memory, root_agent


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
        # Given: A callback context with memory service
        # When: Callback is invoked
        await auto_save_to_memory(mock_callback_context)

        # Then: Should call add_session_to_memory
        mock_callback_context.add_session_to_memory.assert_called_once()

    async def test_auto_save_to_memory_logs_success(
        self, mock_callback_context, caplog
    ):
        """Test callback logs success message."""
        # Given: A callback context with memory service
        # When: Callback is invoked
        with caplog.at_level("INFO"):
            await auto_save_to_memory(mock_callback_context)

        # Then: Should log success
        assert "Session saved to memory successfully" in caplog.text

    async def test_auto_save_to_memory_handles_value_error(
        self, mock_callback_context, caplog
    ):
        """Test callback handles missing memory service gracefully."""
        # Given: A callback context where add_session_to_memory raises ValueError
        mock_callback_context.add_session_to_memory.side_effect = ValueError(
            "memory service is not available"
        )

        # When: Callback is invoked
        with caplog.at_level("WARNING"):
            await auto_save_to_memory(mock_callback_context)

        # Then: Should log warning, not raise
        assert "Could not save to memory" in caplog.text


class TestRootAgentConfiguration:
    """Test suite for root agent memory configuration.

    These tests verify the production root_agent instance has memory
    configured correctly (not just newly-created agent instances).
    """

    def test_root_agent_has_after_agent_callback(self):
        """Test root agent has after_agent_callback configured."""
        # Given: The root agent module
        # Then: Should have the auto_save_to_memory callback
        assert root_agent.after_agent_callback == auto_save_to_memory

    def test_root_agent_search_agent_has_preload_memory_tool(self):
        """Test production search agent includes preload_memory_tool.

        This tests the actual root_agent.sub_agents[0] instance,
        not a newly-created agent from create_search_agent().
        """
        # Given: The production root agent's search sub-agent
        search_agent = root_agent.sub_agents[0]

        # Then: Should include preload_memory_tool
        assert preload_memory_tool in search_agent.tools
