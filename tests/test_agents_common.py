"""Common parametrized tests for both Search and Recommendation agents."""

import pytest
from google.adk.agents import LlmAgent

from src.venue_recommendation_agent.recommendation_agent import create_recommendation_agent
from src.venue_recommendation_agent.search_agent import create_search_agent


@pytest.mark.parametrize(
    "agent_name,create_fn,expected_name,expected_description,expected_temp,expected_top_p,expected_tokens",
    [
        (
            "search_agent",
            create_search_agent,
            "search_agent",
            "Searches for businesses on Yelp based on user queries",
            0.3,
            0.9,
            1024,
        ),
        (
            "recommendation_agent",
            create_recommendation_agent,
            "recommendation_agent",
            "Analyses business data and provides ranked recommendations",
            0.7,
            0.95,
            2048,
        ),
    ],
)
class TestAgentsCommon:
    """Common tests for both Search and Recommendation agents."""

    def test_create_agent_returns_llm_agent(
        self,
        agent_name,
        create_fn,
        expected_name,
        expected_description,
        expected_temp,
        expected_top_p,
        expected_tokens,
    ):
        """Test create agent returns LlmAgent instance with correct config."""
        # Given: Mocked settings (via autouse fixture)
        # When: Agent is created
        agent = create_fn()

        # Then: Should return LlmAgent instance with correct properties
        assert isinstance(agent, LlmAgent)
        assert agent.name == expected_name
        assert agent.description == expected_description

    def test_create_agent_uses_correct_temperature(
        self,
        agent_name,
        create_fn,
        expected_name,
        expected_description,
        expected_temp,
        expected_top_p,
        expected_tokens,
    ):
        """Test create agent uses correct temperature and output tokens."""
        # Given: Mocked settings (via autouse fixture)
        # When: Agent is created
        agent = create_fn()

        # Then: Should use correct temperature and token limits
        assert agent.generate_content_config.temperature == expected_temp
        assert agent.generate_content_config.top_p == expected_top_p
        assert agent.generate_content_config.max_output_tokens == expected_tokens

    def test_create_agent_configures_retry_options(
        self,
        agent_name,
        create_fn,
        expected_name,
        expected_description,
        expected_temp,
        expected_top_p,
        expected_tokens,
    ):
        """Test create agent configures Google API retry options."""
        # Given: Mocked settings (via autouse fixture)
        # When: Agent is created
        agent = create_fn()

        # Then: Should have retry configuration
        http_options = agent.generate_content_config.http_options
        assert http_options is not None
        assert http_options.retry_options is not None
        assert http_options.retry_options.attempts == 3
        assert http_options.retry_options.initial_delay == 1.0
        assert http_options.retry_options.max_delay == 10.0
        assert http_options.retry_options.exp_base == 2.0
        assert http_options.retry_options.jitter == 1.0
        assert 429 in http_options.retry_options.http_status_codes
        assert 500 in http_options.retry_options.http_status_codes

    def test_create_agent_uses_custom_model(
        self,
        agent_name,
        create_fn,
        expected_name,
        expected_description,
        expected_temp,
        expected_top_p,
        expected_tokens,
        mocker,
    ):
        """Test create agent uses custom Gemini model from settings."""
        # Given: Custom model in settings
        mocker.patch(
            f"src.venue_recommendation_agent.{agent_name}.settings.gemini_model",
            "gemini-2.5-flash-lite",
        )

        # When: Agent is created
        agent = create_fn()

        # Then: Should use custom model
        assert agent.model == "gemini-2.5-flash-lite"

    def test_create_agent_accepts_mcp_tools(
        self,
        agent_name,
        create_fn,
        expected_name,
        expected_description,
        expected_temp,
        expected_top_p,
        expected_tokens,
        mocker,
    ):
        """Test create agent accepts MCP tools (search agent only)."""
        # Given: MCP tools
        mock_tools = [mocker.Mock()]

        # When: Agent is created with tools
        if agent_name == "search_agent":
            agent = create_fn(mcp_tools=mock_tools)
            # Then: Search agent should have tools assigned
            assert agent.tools == mock_tools
        else:
            # Recommendation agent doesn't accept tools
            agent = create_fn()
            assert agent.tools == []

    def test_create_agent_without_tools(
        self,
        agent_name,
        create_fn,
        expected_name,
        expected_description,
        expected_temp,
        expected_top_p,
        expected_tokens,
    ):
        """Test create agent works without tools."""
        # When: Agent is created without tools
        if agent_name == "search_agent":
            agent = create_fn(mcp_tools=None)
            # Then: Should have empty tools list
            assert agent.tools == []
        else:
            # Recommendation agent doesn't accept mcp_tools parameter
            agent = create_fn()
            assert agent.tools == []
