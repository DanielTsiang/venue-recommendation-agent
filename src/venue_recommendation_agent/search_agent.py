"""Search Agent for querying Yelp businesses using Google ADK."""

import logging

from google.adk.agents import LlmAgent
from google.genai.types import GenerateContentConfig, HttpOptions, HttpRetryOptions

from src.config import settings
from src.venue_recommendation_agent.prompts.search_agent import SEARCH_AGENT_PROMPT
from src.venue_recommendation_agent.schemas import SearchAgentOutput

logger = logging.getLogger(__name__)


def create_search_agent(mcp_tools: list | None = None) -> LlmAgent:
    """Create a Search Agent for Yelp business queries.

    This agent is designed to be wrapped as an AgentTool by the recommendation
    agent. When invoked as a tool, the search results are returned directly
    to the parent agent without being displayed to the user.

    Args:
        mcp_tools: List of MCP tools available to this agent

    Returns:
        Configured LlmAgent for search tasks
    """
    logger.info(f"Creating Search Agent with model: {settings.gemini_model}")

    # Configure retry options for Google API calls
    retry_options = HttpRetryOptions(
        attempts=3,
        initial_delay=1.0,
        max_delay=10.0,
        exp_base=2.0,
        jitter=True,
        http_status_codes=[
            429,
            500,
            502,
            503,
            504,
        ],  # Retry on rate limit and server errors
    )

    http_options = HttpOptions(
        retry_options=retry_options,
    )

    # Configure generation settings for search tasks
    gen_config = GenerateContentConfig(
        temperature=0.3,  # Lower temperature for deterministic parsing
        top_p=0.9,
        max_output_tokens=32000,
        http_options=http_options,
    )

    tools = mcp_tools or []

    # Create Search Agent
    agent = LlmAgent(
        name="search",
        description="Searches for businesses on Yelp based on user queries",
        model=settings.gemini_model,
        instruction=SEARCH_AGENT_PROMPT,
        tools=tools,
        generate_content_config=gen_config,
        output_schema=SearchAgentOutput
    )

    logger.info("Search Agent created successfully")
    return agent
