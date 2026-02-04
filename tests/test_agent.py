"""Unit tests for root agent configuration (agent.py)."""

from google.adk.tools.agent_tool import AgentTool
from google.adk.tools.preload_memory_tool import preload_memory_tool

from src.venue_recommendation_agent.agent import root_agent
from src.venue_recommendation_agent.recommendation_agent import auto_save_to_memory


class TestRootAgentConfiguration:
    """Test suite for root agent wiring in agent.py.

    These tests verify the production root_agent instance is configured
    correctly with the AgentTool pattern.
    """

    def test_root_agent_is_recommendation_agent(self):
        """Test root agent is the recommendation agent.

        With AgentTool pattern, the recommendation agent is the user-facing
        root agent.
        """
        # Then: Root agent should be named recommendation_agent
        assert root_agent.name == "recommendation_agent"

    def test_root_agent_has_search_tool_and_memory_tool(self):
        """Test root agent has search agent and preload_memory_tool.

        The recommendation agent needs:
        - search tool to find venues
        - preload_memory_tool to automatically inject past context before each turn
        """
        # Then: Should have exactly two tools
        assert len(root_agent.tools) == 2

        # And: Should have preload_memory_tool
        assert preload_memory_tool in root_agent.tools

        # And: Should have an AgentTool wrapping search
        agent_tools = [t for t in root_agent.tools if isinstance(t, AgentTool)]
        assert len(agent_tools) == 1
        assert agent_tools[0].agent.name == "search"

    def test_root_agent_has_memory_callback(self):
        """Test root agent has memory persistence callback configured."""
        # Then: Should have the auto_save_to_memory callback
        assert root_agent.after_agent_callback == auto_save_to_memory
