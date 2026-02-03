"""Unit tests for Search Agent."""

from src.venue_recommendation_agent.search_agent import (
    SEARCH_RESULTS,
    create_search_agent,
    suppress_text_output_callback,
)


class TestSearchAgent:
    """Test suite for Search Agent-specific functionality."""

    def test_create_search_agent_logs_creation(self, caplog):
        """Test create_search_agent logs agent creation."""
        # Given: Mocked settings (via autouse fixture)
        # When: Search agent is created
        with caplog.at_level("INFO"):
            create_search_agent()

        # Then: Should log creation messages
        assert "Creating Search Agent" in caplog.text
        assert "Search Agent created successfully" in caplog.text

    def test_create_search_agent_has_callback(self):
        """Test create_search_agent sets after_model_callback."""
        # Given: Mocked settings (via autouse fixture)
        # When: Search agent is created
        agent = create_search_agent()

        # Then: Should have after_model_callback set to suppress function
        assert agent.after_model_callback == suppress_text_output_callback


class TestSuppressTextOutputCallback:
    """Test suite for suppress_text_output_callback function."""

    def test_suppress_text_output_filters_text_parts_and_updates_state(self, mocker):
        """Test callback removes text parts, preserves function calls, and updates state."""
        # Given: Mock LLM response with both text and function_call parts
        mock_text_part = mocker.Mock()
        mock_text_part.text = "This is some text"

        mock_function_part = mocker.Mock()
        mock_function_part.text = None

        mock_content = mocker.Mock()
        mock_content.parts = [mock_text_part, mock_function_part]

        mock_llm_response = mocker.Mock()
        mock_llm_response.content = mock_content

        mock_callback_context = mocker.Mock()
        mock_callback_context.state = mocker.Mock()

        # When: Callback is invoked
        suppress_text_output_callback(mock_llm_response, mock_callback_context)

        # Then: Should update state with text content
        mock_callback_context.state.update.assert_called_once_with(
            {SEARCH_RESULTS: "This is some text"}
        )
        # And should filter out text parts (only function call remains)
        assert len(mock_content.parts) == 1
        assert mock_content.parts[0] == mock_function_part

    def test_suppress_text_output_handles_none_response(self, mocker):
        """Test callback handles None llm_response gracefully."""
        # Given: None LLM response
        mock_callback_context = mocker.Mock()

        # When: Callback is invoked
        # Then: Should not raise error
        suppress_text_output_callback(None, mock_callback_context)

    def test_suppress_text_output_handles_no_content(self, mocker):
        """Test callback handles llm_response without content attribute."""
        # Given: Mock response without content
        mock_llm_response = mocker.Mock()
        mock_llm_response.content = None

        mock_callback_context = mocker.Mock()

        # When: Callback is invoked
        # Then: Should not raise error
        suppress_text_output_callback(mock_llm_response, mock_callback_context)

    def test_suppress_text_output_handles_no_parts(self, mocker):
        """Test callback handles content without parts attribute."""
        # Given: Mock content without parts
        mock_content = mocker.Mock()
        mock_content.parts = None

        mock_llm_response = mocker.Mock()
        mock_llm_response.content = mock_content

        mock_callback_context = mocker.Mock()

        # When: Callback is invoked
        # Then: Should not raise error
        suppress_text_output_callback(mock_llm_response, mock_callback_context)

    def test_suppress_text_output_combines_multiple_text_parts(self, mocker):
        """Test callback combines multiple text parts into single state entry."""
        # Given: Mock response with multiple text parts
        mock_text_part1 = mocker.Mock()
        mock_text_part1.text = "First text"

        mock_text_part2 = mocker.Mock()
        mock_text_part2.text = "Second text"

        mock_function_part = mocker.Mock()
        mock_function_part.text = None

        mock_content = mocker.Mock()
        mock_content.parts = [mock_text_part1, mock_text_part2, mock_function_part]

        mock_llm_response = mocker.Mock()
        mock_llm_response.content = mock_content

        mock_callback_context = mocker.Mock()
        mock_callback_context.state = mocker.Mock()

        # When: Callback is invoked
        suppress_text_output_callback(mock_llm_response, mock_callback_context)

        # Then: Should combine texts with newline and update state
        mock_callback_context.state.update.assert_called_once_with(
            {SEARCH_RESULTS: "First text\nSecond text"}
        )
        # And should filter out all text parts
        assert len(mock_content.parts) == 1
        assert mock_content.parts[0] == mock_function_part

    def test_suppress_text_output_handles_only_function_calls(self, mocker):
        """Test callback handles response with no text parts (only function calls)."""
        # Given: Mock response with only function call parts
        mock_function_part = mocker.Mock()
        mock_function_part.text = None

        mock_content = mocker.Mock()
        mock_content.parts = [mock_function_part]

        mock_llm_response = mocker.Mock()
        mock_llm_response.content = mock_content

        mock_callback_context = mocker.Mock()
        mock_callback_context.state = mocker.Mock()

        # When: Callback is invoked
        suppress_text_output_callback(mock_llm_response, mock_callback_context)

        # Then: Should not update state (no text to save)
        mock_callback_context.state.update.assert_not_called()
        # And parts should remain unchanged
        assert len(mock_content.parts) == 1
        assert mock_content.parts[0] == mock_function_part
