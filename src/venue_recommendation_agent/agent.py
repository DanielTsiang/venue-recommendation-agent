"""Agent configuration for venue recommendation system.

Creates the root RecommendationAgent with SearchAgent as an AgentTool.
MCP server auto-launches as subprocess for Yelp API access.
"""

import logging
import os
import sys
from pathlib import Path

import uvicorn
from google.adk.apps import App
from google.adk.apps.app import EventsCompactionConfig
from google.adk.apps.llm_event_summarizer import LlmEventSummarizer
from google.adk.cli.fast_api import get_fast_api_app
from google.adk.models import Gemini
from google.adk.tools.agent_tool import AgentTool
from google.adk.tools.mcp_tool import McpToolset, StdioConnectionParams
from google.adk.tools.preload_memory_tool import preload_memory_tool
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


# Create MCP toolset for Yelp API access
_mcp_toolset = create_mcp_toolset()

# Search agent (runs as a tool, output hidden from user)
_search_agent = create_search_agent(mcp_tools=[_mcp_toolset])
_search_agent_tool = AgentTool(agent=_search_agent)

# Recommendation agent is the root (user-facing) agent.
# It uses the search agent as a tool to find venues, then provides recommendations.
# The preload_memory_tool automatically injects past context before each turn.
root_agent = create_recommendation_agent(
    tools=[_search_agent_tool, preload_memory_tool]
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
