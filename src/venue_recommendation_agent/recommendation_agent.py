"""Recommendation Agent for analysing and ranking venues using Google ADK."""

import logging

from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.genai.types import GenerateContentConfig, HttpOptions, HttpRetryOptions

from src.config import settings
from src.venue_recommendation_agent.prompts.recommendation_agent import (
    RECOMMENDATION_AGENT_PROMPT,
)

logger = logging.getLogger(__name__)


def create_recommendation_agent(tools: list | None = None) -> LlmAgent:
    """Create a Recommendation Agent for analysing venues.

    This agent serves as the user-facing root agent. It uses the search agent
    (wrapped as an AgentTool) to find venues, then analyses the results and
    provides ranked recommendations.

    The agent automatically saves sessions to memory after each turn via
    the auto_save_to_memory callback.

    Args:
        tools: List of tools available to this agent

    Returns:
        Configured LlmAgent for recommendation tasks
    """
    logger.info(f"Creating Recommendation Agent with model: {settings.gemini_model}")

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
        tools=tools or [],
        generate_content_config=gen_config,
        after_agent_callback=auto_save_to_memory,
    )

    logger.info("Recommendation Agent created successfully")
    return agent


async def auto_save_to_memory(callback_context: CallbackContext) -> None:
    """Automatically save session to memory after each agent turn.

    This callback is invoked after the agent completes, saving the full
    conversation to memory. The PreloadMemoryTool automatically retrieves
    relevant memories at the start of each turn and injects them into the
    system instruction - no explicit tool call is needed.

    Args:
        callback_context: Context providing access to session and memory service.
    """
    try:
        # Log session details
        session = callback_context._invocation_context.session
        memory_key = f"{session.app_name}/{session.user_id}"
        logger.debug(
            f"Saving to memory - memory_key: {memory_key}, session_id: {session.id}"
        )
        await callback_context.add_session_to_memory()

        # Log what's stored in memory
        memory_service = callback_context._invocation_context.memory_service
        if hasattr(memory_service, "_session_events"):
            stored_keys = list(memory_service._session_events.keys())
            logger.debug(f"Memory now contains keys: {stored_keys}")

        logger.info("Session saved to memory successfully")
    except ValueError as e:
        logger.warning(f"Could not save to memory: {e}")
