"""Unit tests for Recommendation Agent."""

from src.venue_recommendation_agent.recommendation_agent import (
    create_recommendation_agent,
)


class TestRecommendationAgent:
    """Test suite for Recommendation Agent-specific functionality."""

    def test_create_recommendation_agent_logs_creation(self, caplog):
        """Test create_recommendation_agent logs agent creation."""
        # Given: Mocked settings (via autouse fixture)
        # When: Recommendation agent is created
        with caplog.at_level("INFO"):
            create_recommendation_agent()

        # Then: Should log creation messages
        assert "Creating Recommendation Agent" in caplog.text
        assert "Recommendation Agent created successfully" in caplog.text

    def test_recommendation_agent_temperature_higher_than_search(self):
        """Test recommendation agent uses higher temperature than search agent."""
        # Given: Mocked settings (via autouse fixture)
        from src.venue_recommendation_agent.search_agent import create_search_agent

        # When: Both agents are created
        search_agent = create_search_agent()
        recommendation_agent = create_recommendation_agent()

        # Then: Recommendation agent should have higher temperature for creativity
        assert (
            recommendation_agent.generate_content_config.temperature
            > search_agent.generate_content_config.temperature
        )
        assert recommendation_agent.generate_content_config.temperature == 0.7
        assert search_agent.generate_content_config.temperature == 0.3

    def test_recommendation_agent_has_larger_output_tokens(self):
        """Test recommendation agent allows more output tokens than search agent."""
        # Given: Mocked settings (via autouse fixture)
        from src.venue_recommendation_agent.search_agent import create_search_agent

        # When: Both agents are created
        search_agent = create_search_agent()
        recommendation_agent = create_recommendation_agent()

        # Then: Recommendation agent should allow more output for detailed analysis
        assert (
            recommendation_agent.generate_content_config.max_output_tokens
            > search_agent.generate_content_config.max_output_tokens
        )
        assert recommendation_agent.generate_content_config.max_output_tokens == 2048
        assert search_agent.generate_content_config.max_output_tokens == 1024
