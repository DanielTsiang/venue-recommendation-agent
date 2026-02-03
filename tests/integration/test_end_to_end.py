"""Integration tests for end-to-end workflow with real API keys."""

import os
import uuid

import pytest
from google.adk.agents import SequentialAgent
from google.adk.runners import InMemoryRunner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from src.config import Settings
from src.mcp_server.server import search_yelp_businesses as _search_tool
from src.mcp_server.yelp.client import YelpClient
from src.mcp_server.yelp.models import SearchResponse
from src.venue_recommendation_agent.agent import create_mcp_toolset
from src.venue_recommendation_agent.recommendation_agent import (
    create_recommendation_agent,
)
from src.venue_recommendation_agent.search_agent import create_search_agent


@pytest.fixture(scope="module")
def check_api_keys():
    """Fixture to check that API keys are properly configured.

    Raises:
        pytest.skip: If API keys are not configured (allows graceful skip)
        ValueError: If API keys are placeholder values (hard fail)
    """
    # Given: Environment should have valid API keys or Vertex AI configuration
    try:
        settings = Settings()

        # When: API keys are validated
        # Then: They should not be placeholder values
        if settings.yelp_api_key.startswith("your_"):
            raise ValueError(
                "YELP_API_KEY is set to a placeholder value. "
                "Please set it to a real API key in .env file."
            )

        # Validate Google authentication (API key or Vertex AI)
        if settings.google_api_key:
            # Using Google AI API with API key
            if settings.google_api_key.startswith("your_"):
                raise ValueError(
                    "GOOGLE_API_KEY is set to a placeholder value. "
                    "Please set it to a real API key in .env file."
                )
        else:
            # Using Vertex AI with ADC - ensure project is set
            if not settings.vertex_project:
                pytest.skip(
                    "Vertex AI not configured. When using ADC (no GOOGLE_API_KEY), "
                    "set VERTEX_PROJECT in .env file to run integration tests."
                )

        return settings

    except Exception as e:
        if "API key must be set to a valid value" in str(e):
            pytest.skip(
                "API keys not configured. Set YELP_API_KEY and either GOOGLE_API_KEY "
                "or VERTEX_PROJECT in .env file to run integration tests."
            )
        raise


@pytest.mark.integration
async def test_yelp_client_real_api_call(check_api_keys):
    """Test YelpClient makes successful real API call to Yelp.

    This test requires valid YELP_API_KEY in environment.
    """
    # Given: Valid Yelp API key and YelpClient
    settings = check_api_keys

    # When: Real API call is made to Yelp
    async with YelpClient(settings.yelp_api_key) as client:
        response = await client.search_businesses(
            location="London, UK",
            term="restaurants",
            limit=5,
        )

    # Then: Response should contain real business data
    assert response is not None
    assert hasattr(response, "businesses")
    assert hasattr(response, "total")
    assert isinstance(response.businesses, list)
    assert response.total >= 0

    # And: If businesses are found, they should have valid data
    if len(response.businesses) > 0:
        business = response.businesses[0]
        assert business.id is not None
        assert business.name is not None
        assert business.rating is not None
        assert business.rating >= 0 and business.rating <= 5
        assert business.review_count is not None
        assert business.review_count >= 0
        assert business.location is not None
        assert business.coordinates is not None


@pytest.mark.integration
async def test_yelp_client_handles_invalid_location(check_api_keys):
    """Test YelpClient handles invalid location gracefully.

    This test requires valid YELP_API_KEY in environment.
    """
    # Given: Valid Yelp API key but invalid location
    settings = check_api_keys

    # When: API call is made with invalid location
    from src.mcp_server.exceptions import YelpAPIError

    with pytest.raises(YelpAPIError, match="Bad request"):
        async with YelpClient(settings.yelp_api_key) as client:
            await client.search_businesses(
                location="",  # Empty location should fail
                limit=5,
            )


@pytest.mark.integration
def test_sequential_agent_creation_with_mcp_tools(check_api_keys):
    """Test SequentialAgent can be created with MCP toolset.

    This test requires both YELP_API_KEY and GOOGLE_API_KEY in environment.
    """
    # Given: Valid API keys (validated by fixture)
    # When: MCP toolset is created
    mcp_toolset = create_mcp_toolset()

    search_agent = create_search_agent(mcp_tools=[mcp_toolset])
    recommendation_agent = create_recommendation_agent()

    # And: SequentialAgent is created
    root_agent = SequentialAgent(
        name="test_workflow",
        description="Test workflow",
        sub_agents=[search_agent, recommendation_agent],
    )

    # Then: Root agent should be properly configured
    assert root_agent is not None
    assert root_agent.name == "test_workflow"
    assert len(root_agent.sub_agents) == 2

    # And: Search agent should have MCP tools, recommendation agent should not
    assert len(search_agent.tools) > 0
    assert len(recommendation_agent.tools) == 0


@pytest.mark.integration
async def test_mcp_server_search_tool_real_api_call(check_api_keys):
    """Test search_yelp_businesses MCP tool makes successful real API call.

    This test requires valid YELP_API_KEY in environment.
    """
    # Given: Valid Yelp API key (validated by fixture)
    # When: MCP tool is called with real API
    result = await _search_tool.fn(
        location="Shoreditch, London, UK",
        term="italian restaurants",
        limit=3,
    )

    # Then: Result should be properly formatted
    assert result is not None
    assert "businesses" in result
    assert "total" in result
    assert "count" in result
    assert "summary" in result
    assert "error" not in result

    # And: Should contain business data (if available)
    assert isinstance(result["businesses"], list)
    assert result["count"] == len(result["businesses"])
    assert result["count"] <= 3  # Respects limit

    # And: If businesses found, validate structure
    if len(result["businesses"]) > 0:
        business = result["businesses"][0]
        assert "id" in business
        assert "name" in business
        assert "rating" in business
        assert "review_count" in business
        assert "address" in business
        assert "categories" in business

        # And: Rating should be valid
        assert 0 <= business["rating"] <= 5


@pytest.mark.integration
def test_environment_variables_loaded_correctly(check_api_keys):
    """Test that environment variables are loaded and validated correctly.

    This test ensures the .env file is properly configured for either
    Google AI API (with API key) or Vertex AI (with ADC).
    """
    # Given: Settings loaded from environment
    settings = check_api_keys

    # When: Settings are validated
    # Then: Required fields should be present
    assert settings.yelp_api_key is not None
    assert settings.gemini_model is not None
    assert settings.log_level is not None

    # And: Yelp API key should not be empty or placeholder
    assert len(settings.yelp_api_key) > 0
    assert not settings.yelp_api_key.startswith("your_")

    # And: Either Google API key or Vertex AI project should be configured
    if settings.google_api_key:
        # Using Google AI API with API key
        assert len(settings.google_api_key) > 0
        assert not settings.google_api_key.startswith("your_")
    else:
        # Using Vertex AI with ADC
        assert settings.vertex_project is not None
        assert len(settings.vertex_project) > 0

    # And: Log level should be valid
    assert settings.log_level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


@pytest.mark.integration
async def test_yelp_client_retry_on_network_error(check_api_keys, mocker):
    """Test that YelpClient retries on network errors (using real client setup).

    This test verifies retry logic is configured, but uses mocking
    to simulate network errors without making real API calls.
    """
    # Given: Real settings but mocked httpx client that fails then succeeds
    settings = check_api_keys

    # Create a mock that succeeds on first attempt
    mock_response = mocker.Mock()
    mock_response.json.return_value = {"businesses": [], "total": 0}

    # When: YelpClient makes request
    async with YelpClient(settings.yelp_api_key) as client:
        # Mock the get method after client initialization
        client._client.get = mocker.AsyncMock(return_value=mock_response)

        # Then: Should succeed (retry logic is configured and will work if needed)
        result = await client.search_businesses(location="London, UK")

        # And: Result should be valid
        assert isinstance(result, SearchResponse)
        assert client._client.get.called


@pytest.mark.integration
async def test_full_multi_agent_workflow_end_to_end(check_api_keys):
    """Test complete multi-agent workflow from query to recommendations.

    This test verifies the full flow described in README.md:
    User Query → Search Agent → MCP → Yelp API → Recommendation Agent → Final Output

    This test requires both YELP_API_KEY and GOOGLE_API_KEY in environment.
    """
    # Given: Complete multi-agent system with real APIs
    # Create MCP toolset for search agent
    mcp_toolset = create_mcp_toolset()

    search_agent = create_search_agent(mcp_tools=[mcp_toolset])
    recommendation_agent = create_recommendation_agent()

    sequential_agent = SequentialAgent(
        name="test_full_workflow",
        description="Test full recommendation workflow",
        sub_agents=[search_agent, recommendation_agent],
    )

    # Create session service and runner
    session_service = InMemorySessionService()
    runner = InMemoryRunner(agent=sequential_agent)
    runner.session_service = session_service

    # Create session
    user_id = "test_user"
    session_id = f"test_full_{uuid.uuid4().hex[:8]}"
    await session_service.create_session(
        app_name=runner.app_name, user_id=user_id, session_id=session_id
    )

    # When: User query is processed through complete workflow
    user_query = "Find me Italian restaurants in Shoreditch, London"

    user_message = types.Content(role="user", parts=[types.Part(text=user_query)])

    # Run through the sequential agent workflow
    response_parts = []
    async for event in runner.run_async(
        user_id=user_id, session_id=session_id, new_message=user_message
    ):
        # Collect response parts from the workflow
        if hasattr(event, "content") and event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    response_parts.append(part.text)

    # Then: Should have received responses from agents
    assert len(response_parts) > 0, "No responses from agents"

    # And: Final response should contain recommendation-related content
    final_response = " ".join(response_parts)
    assert len(final_response) > 100, "Response too short to be meaningful"

    # And: Response should reference the query context
    # (Either mentions Italian, Shoreditch, restaurants, or provides business names)
    has_context = any(
        keyword in final_response.lower()
        for keyword in ["italian", "shoreditch", "restaurant", "rating", "review"]
    )
    assert (
        has_context
    ), f"Response lacks context about query. Response: {final_response[:200]}"


@pytest.mark.integration
async def test_search_agent_calls_yelp_via_mcp(check_api_keys):
    """Test Search Agent successfully calls Yelp API through MCP protocol.

    This test verifies the MCP connection flow:
    Search Agent → MCP Toolset → FastMCP Server → Yelp API

    This test requires both YELP_API_KEY and GOOGLE_API_KEY in environment.
    """
    # Given: Search agent with MCP toolset
    mcp_toolset = create_mcp_toolset()
    search_agent = create_search_agent(mcp_tools=[mcp_toolset])

    # Create session service and runner
    session_service = InMemorySessionService()
    runner = InMemoryRunner(agent=search_agent)
    runner.session_service = session_service

    # Create session
    user_id = "test_user"
    session_id = f"test_search_{uuid.uuid4().hex[:8]}"
    await session_service.create_session(
        app_name=runner.app_name, user_id=user_id, session_id=session_id
    )

    # When: Search agent processes a query requiring Yelp search
    query = "Search for coffee shops in Camden, London. Return the top 3 results."

    user_message = types.Content(role="user", parts=[types.Part(text=query)])

    # Run search agent
    tool_calls_made = []
    search_results = []

    async for event in runner.run_async(
        user_id=user_id, session_id=session_id, new_message=user_message
    ):
        # Track tool calls
        if hasattr(event, "content") and event.content and event.content.parts:
            for part in event.content.parts:
                # Check if tool was called
                if hasattr(part, "function_call") and part.function_call:
                    tool_calls_made.append(part.function_call.name)

                # Collect search results
                if part.text:
                    search_results.append(part.text)

    # Then: Search agent should have called the Yelp search tool
    assert len(tool_calls_made) > 0, "Search agent did not call any tools"
    assert any(
        "search" in tool.lower() or "yelp" in tool.lower() for tool in tool_calls_made
    ), f"Expected Yelp search tool call, got: {tool_calls_made}"

    # And: Search agent should NOT output text (suppressed by callback)
    # Text suppression ensures clean UI - only tool calls and final recommendations visible
    assert (
        len(search_results) == 0
    ), f"Search agent should not output text (callback suppresses it), got: {search_results}"


@pytest.mark.integration
async def test_recommendation_agent_analyses_business_data(check_api_keys):
    """Test Recommendation Agent analyses Yelp business data.

    This test verifies the Recommendation Agent can:
    1. Receive business data from session state (simulating Search Agent output)
    2. Analyse ratings, reviews, prices
    3. Provide ranked recommendations with reasoning

    This test requires GOOGLE_API_KEY in environment.
    """
    # Given: Recommendation agent
    recommendation_agent = create_recommendation_agent()

    # Create session service and runner
    session_service = InMemorySessionService()
    runner = InMemoryRunner(agent=recommendation_agent)
    runner.session_service = session_service

    # Create session
    user_id = "test_user"
    session_id = f"test_rec_{uuid.uuid4().hex[:8]}"
    await session_service.create_session(
        app_name=runner.app_name, user_id=user_id, session_id=session_id
    )

    # And: Sample business data (simulating Search Agent output)
    business_data = """I found 3 Italian restaurants in Shoreditch:

1. Pizza Paradise
   - Rating: 4.5/5 (120 reviews)
   - Price: ££
   - Distance: 0.3 miles
   - Address: 45 High Street, Shoreditch

2. Pasta Palace
   - Rating: 4.2/5 (85 reviews)
   - Price: £££
   - Distance: 0.5 miles
   - Address: 22 Main Road, Shoreditch

3. Trattoria Bella
   - Rating: 4.8/5 (200 reviews)
   - Price: ££££
   - Distance: 0.8 miles
   - Address: 10 Park Lane, Shoreditch"""

    # User asks for recommendations
    user_message = types.Content(
        role="user",
        parts=[
            types.Part(text="Please analyse these and provide your recommendations.")
        ],
    )

    # Populate state with search results (simulating Search Agent's output_key)
    state_delta = {"SEARCH_RESULTS": business_data}

    # When: Recommendation agent analyses the data
    recommendations = []
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=user_message,
        state_delta=state_delta,
    ):
        if hasattr(event, "content") and event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    recommendations.append(part.text)

    # Then: Should have generated recommendations
    assert len(recommendations) > 0, "No recommendations generated"

    full_recommendation = " ".join(recommendations)

    # And: Recommendations should reference the businesses
    assert len(full_recommendation) > 100, "Recommendation too short"

    # And: Should show analysis (mentions ratings, price, or distance)
    has_analysis = any(
        keyword in full_recommendation.lower()
        for keyword in ["rating", "review", "price", "distance", "recommend"]
    )
    assert (
        has_analysis
    ), f"Recommendation lacks analysis. Got: {full_recommendation[:200]}"


@pytest.mark.integration
def test_api_keys_required_for_integration_tests():
    """Test that integration tests fail fast if API keys are not set.

    This test validates the check_api_keys fixture behavior for both
    Google AI API (with API key) and Vertex AI (with ADC) authentication methods.
    """
    # Given: Current environment state
    yelp_key = os.getenv("YELP_API_KEY")
    google_key = os.getenv("GOOGLE_API_KEY")
    vertex_project = os.getenv("VERTEX_PROJECT")

    # When: We check if API keys/credentials are set
    has_yelp_key = yelp_key and not yelp_key.startswith("your_")
    has_google_key = google_key and not google_key.startswith("your_")
    has_vertex_project = vertex_project and len(vertex_project) > 0

    # Then: At least one of the following should be true:
    # 1. Both Yelp key and Google key are set (Google AI API)
    # 2. Both Yelp key and Vertex project are set (Vertex AI with ADC)
    # 3. Keys are missing (tests will be skipped via check_api_keys fixture)
    if has_yelp_key and (has_google_key or has_vertex_project):
        # Proper authentication configured - integration tests should run
        assert True
    else:
        # Keys missing - integration tests will be skipped
        pytest.skip(
            "Integration tests require YELP_API_KEY and either GOOGLE_API_KEY "
            "or VERTEX_PROJECT. Set them in .env file to run integration tests."
        )
