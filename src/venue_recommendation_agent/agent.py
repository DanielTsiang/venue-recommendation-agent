"""Agent configuration for venue recommendation system.

Creates the root SequentialAgent connecting search and recommendation agents.
MCP server auto-launches as subprocess for Yelp API access.
"""

import logging
import os
import sys
from pathlib import Path

import uvicorn
from google.adk.agents import SequentialAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.apps.app import EventsCompactionConfig
from google.adk.apps.llm_event_summarizer import LlmEventSummarizer
from google.adk.cli.fast_api import get_fast_api_app
from google.adk.models import Gemini
from google.adk.tools.mcp_tool import McpToolset, StdioConnectionParams
from mcp.client.stdio import StdioServerParameters

from src.config import settings
from src.venue_recommendation_agent.recommendation_agent import (
    create_recommendation_agent,
)
from src.venue_recommendation_agent.search_agent import create_search_agent

logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)


def create_mcp_toolset() -> McpToolset:
    """Create MCP toolset for connecting to Yelp FastMCP server.

    Returns:
        Configured McpToolset instance
    """
    server_params = StdioServerParameters(
        command="uv",
        args=["run", "mcp-server"],
        env=dict(os.environ),
    )

    connection_params = StdioConnectionParams(
        server_params=server_params,
        timeout=10.0,
    )

    return McpToolset(connection_params=connection_params)


async def auto_save_to_memory(callback_context: CallbackContext) -> None:
    """Automatically save session to memory after each agent turn.

    This callback is invoked after the root SequentialAgent completes,
    saving the full conversation to memory for future recall via PreloadMemoryTool.

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


_mcp_toolset = create_mcp_toolset()

_search_agent = create_search_agent(mcp_tools=[_mcp_toolset])
_recommendation_agent = create_recommendation_agent()

# SequentialAgent orchestrates two-phase workflow:
# 1. Search Agent: Queries Yelp API, stores results in state via after_model_callback
#    - Text output suppressed (only tool calls visible in UI)
#    - PreloadMemoryTool retrieves relevant past conversations
# 2. Recommendation Agent: Analyzes stored results, provides final recommendations
#    - Receives text summary from state + full tool responses from conversation history
# 3. After completion: auto_save_to_memory saves session for future recall
root_agent = SequentialAgent(
    name="venue_recommendation_workflow",
    description="Sequential workflow for finding and recommending venues",
    sub_agents=[
        _search_agent,
        _recommendation_agent,
    ],
    after_agent_callback=auto_save_to_memory,
)

# Summariser for condensing earlier conversation turns
summarization_llm = LlmEventSummarizer(llm=Gemini(model=settings.gemini_model))

app = App(
    name="venue_recommendation_agent",
    root_agent=root_agent,
    # Compact events every 5 turns to reduce context size
    events_compaction_config=EventsCompactionConfig(
        compaction_interval=5,
        overlap_size=1,  # Keep 1 previous turn for context
        summarizer=summarization_llm,
    ),
)


def main(agents_dir: str | None = None):
    """Launch the Google ADK Web UI.

    Args:
        agents_dir: Path to agents directory (defaults to src/)
    """
    print("=" * 80)
    print("🏪 Venue Recommendation Agent - Google ADK Web UI")
    print("=" * 80)
    print()
    print("Starting Google ADK web server...")
    print()
    print("Once the server is running, you can:")
    print("  1. Use natural language to find restaurants in London")
    print("  2. Get personalised recommendations with detailed analysis")
    print("  3. View conversation history and session management")
    print()
    print("Example queries to try:")
    print('  • "Find romantic Italian restaurants for a date night in Shoreditch"')
    print('  • "Best coffee shops with WiFi near Covent Garden"')
    print('  • "Affordable sushi places in Camden"')
    print()
    print("=" * 80)
    print()

    # Default to src/ directory (contains venue_recommendation_agent)
    agents_path: Path = Path(agents_dir) if agents_dir else Path(__file__).parent.parent

    # Check if agents directory exists
    if not agents_path.exists():
        print(f"❌ Error: Agents directory not found at {agents_path}")
        sys.exit(1)

    # Configuration
    port = 8000
    host = "127.0.0.1"
    url = f"http://{host}:{port}"

    print(f"🌐 Web UI will be available at: {url}")
    print(f"📁 Agents directory: {agents_path}")
    print()
    print(f"👉 Open your browser and navigate to: {url}")
    print()
    print("Press Ctrl+C to stop the server")
    print("=" * 80)
    print()

    try:
        # Create FastAPI app with Google ADK web UI
        web_app = get_fast_api_app(
            agents_dir=str(agents_path),
            web=True,
            host=host,
            port=port,
            reload_agents=True,
        )

        # Run the server with uvicorn
        uvicorn.run(
            web_app,
            host=host,
            port=port,
            log_level="info",
        )

    except KeyboardInterrupt:
        print("\n\n" + "=" * 80)
        print("🛑 Server stopped by user")
        print("=" * 80)
        sys.exit(0)

    except Exception as e:
        print(f"\n❌ Error running ADK web server: {e}")
        print("\nTroubleshooting:")
        print("  1. Ensure you have activated the virtual environment")
        print("  2. Check that google-adk is installed: uv pip list | grep google-adk")
        print("  3. Verify your .env file has the required API keys")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    """Launch the web UI when run as a script."""
    main()
