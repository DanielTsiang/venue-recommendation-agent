"""Search Agent for querying Yelp businesses using Google ADK."""

import logging

from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.llm_agent import LlmResponse
from google.adk.tools.preload_memory_tool import preload_memory_tool
from google.genai.types import GenerateContentConfig, HttpOptions, HttpRetryOptions

from src.config import settings
from src.venue_recommendation_agent.prompts.search_agent import SEARCH_AGENT_PROMPT

logger = logging.getLogger(__name__)

# State key for storing search results (accessible via {SEARCH_RESULTS} in prompts)
SEARCH_RESULTS = "SEARCH_RESULTS"


def create_search_agent(mcp_tools: list | None = None) -> LlmAgent:
    """Create a Search Agent for Yelp business queries.

    Uses MCP tools to query Yelp API. Saves text summary to state for recommendation
    agent prompt injection. Full tool responses remain in conversation history.
    Suppresses text output in UI for clean UX.

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
        max_output_tokens=1024,
        http_options=http_options,
    )

    # Combine memory tool with MCP tools
    tools = [preload_memory_tool]
    if mcp_tools:
        tools.extend(mcp_tools)

    # Create Search Agent
    agent = LlmAgent(
        name="search_agent",
        description="Searches for businesses on Yelp based on user queries",
        model=settings.gemini_model,
        instruction=SEARCH_AGENT_PROMPT,
        tools=tools,
        generate_content_config=gen_config,
        after_model_callback=suppress_text_output_callback,  # Manually saves state and suppresses UI
        output_key=SEARCH_RESULTS,
    )

    logger.info("Search Agent created successfully")
    return agent


def suppress_text_output_callback(
    llm_response: LlmResponse,
    callback_context: CallbackContext,
) -> None:
    """Suppress text output while preserving it in state.

    Saves LLM-generated text (search summaries) to state for prompt injection.
    Tool responses remain in conversation history. Filters text from UI to show
    only tool calls.

    Args:
        llm_response: LLM response with content to filter
        callback_context: Context containing state

    Returns:
        None - modifies llm_response in-place
    """
    if not llm_response or not llm_response.content or not llm_response.content.parts:
        logger.debug("No LLM response content to process")
        return

    # Extract all text parts and combine them
    text_parts = [part.text for part in llm_response.content.parts if part.text]

    if text_parts:
        # Save text summary to state (injected into recommendation agent's prompt)
        # Note: Full tool responses remain in conversation history automatically
        combined_text = "\n".join(text_parts)
        callback_context.state.update({SEARCH_RESULTS: combined_text})
        logger.debug(
            f"Saved {len(combined_text)} characters to state[{SEARCH_RESULTS}]"
        )

        # Filter out text parts from response (keep only function calls)
        filtered_parts = [part for part in llm_response.content.parts if not part.text]
        llm_response.content.parts = filtered_parts

        logger.debug(
            f"Suppressed {len(text_parts)} text parts from UI "
            f"(tool calls preserved: {len(filtered_parts)})"
        )
    else:
        logger.debug("No text parts to suppress")
