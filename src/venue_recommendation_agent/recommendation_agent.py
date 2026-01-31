"""Recommendation Agent for analysing and ranking venues using Google ADK."""

import logging

from google.adk.agents import LlmAgent
from google.genai.types import GenerateContentConfig, HttpOptions, HttpRetryOptions

from src.config import settings
from src.venue_recommendation_agent.prompts.recommendation_agent import (
    RECOMMENDATION_AGENT_PROMPT,
)

logger = logging.getLogger(__name__)


def create_recommendation_agent() -> LlmAgent:
    """Create a Recommendation Agent for analysing venues.

    Receives search summary from state (via {SEARCH_RESULTS} template) and full
    tool responses from conversation history. Provides ranked recommendations.

    Returns:
        Configured LlmAgent for recommendation tasks
    """
    logger.info(
        f"Creating Google ADK RecommendationAgent with model: {settings.gemini_model}"
    )

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

    # Configure generation settings for recommendation tasks
    gen_config = GenerateContentConfig(
        temperature=0.7,  # Balanced temperature for creative recommendations
        top_p=0.95,
        max_output_tokens=2048,
        http_options=http_options,
    )

    agent = LlmAgent(
        name="recommendation_agent",
        description="Analyses business data and provides ranked recommendations",
        model=settings.gemini_model,
        instruction=RECOMMENDATION_AGENT_PROMPT,
        generate_content_config=gen_config,
    )

    logger.info("Google ADK RecommendationAgent created successfully")
    return agent
