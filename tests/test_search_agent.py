"""Unit tests for Search Agent."""

from google.adk.agents import LlmAgent

from src.venue_recommendation_agent.schemas import SearchAgentOutput
from src.venue_recommendation_agent.search_agent import create_search_agent


class TestSearchAgent:
    """Test suite for search_agent.py functionality."""

    def test_create_search_agent_returns_llm_agent(self):
        """Test create_search_agent returns properly configured LlmAgent."""
        # When: Search agent is created
        agent = create_search_agent()

        # Then: Should return LlmAgent with correct properties
        assert isinstance(agent, LlmAgent)
        assert agent.name == "search"

    def test_create_search_agent_logs_creation(self, caplog):
        """Test create_search_agent logs agent creation."""
        # When: Search agent is created
        with caplog.at_level("INFO"):
            create_search_agent()

        # Then: Should log creation messages
        assert "Creating Search Agent" in caplog.text
        assert "Search Agent created successfully" in caplog.text

    def test_search_agent_uses_low_temperature(self):
        """Test search agent uses low temperature for deterministic parsing."""
        # When: Search agent is created
        agent = create_search_agent()

        # Then: Should use low temperature for accurate parameter extraction
        assert agent.generate_content_config.temperature == 0.3
        assert agent.generate_content_config.top_p == 0.9
        assert agent.generate_content_config.max_output_tokens == 32000

    def test_search_agent_configures_retry_options(self):
        """Test search agent configures Google API retry options."""
        # When: Search agent is created
        agent = create_search_agent()

        # Then: Should have retry configuration
        http_options = agent.generate_content_config.http_options
        assert http_options is not None
        assert http_options.retry_options is not None
        assert http_options.retry_options.attempts == 3
        assert http_options.retry_options.initial_delay == 1.0
        assert http_options.retry_options.max_delay == 10.0
        assert 429 in http_options.retry_options.http_status_codes
        assert 500 in http_options.retry_options.http_status_codes

    def test_search_agent_uses_custom_model(self, mocker):
        """Test search agent uses custom Gemini model from settings."""
        # Given: Custom model in settings
        mocker.patch(
            "src.venue_recommendation_agent.search_agent.settings.gemini_model",
            "gemini-2.5-flash-lite",
        )

        # When: Search agent is created
        agent = create_search_agent()

        # Then: Should use custom model
        assert agent.model == "gemini-2.5-flash-lite"

    def test_search_agent_accepts_mcp_tools(self, mocker):
        """Test search agent accepts MCP tools parameter."""
        # Given: Mock MCP tool
        mock_tool = mocker.Mock()

        # When: Search agent is created with MCP tools
        agent = create_search_agent(mcp_tools=[mock_tool])

        # Then: Should only have the MCP tool (no memory tool)
        assert len(agent.tools) == 1
        assert agent.tools[0] == mock_tool

    def test_search_agent_has_output_schema(self):
        """Test search agent has SearchResponse as output_schema.

        The output_schema ensures the agent returns structured JSON
        matching the Yelp API response format.
        """
        # When: Search agent is created
        agent = create_search_agent()

        # Then: Should have SearchAgentOutput as output_schema
        assert agent.output_schema == SearchAgentOutput
