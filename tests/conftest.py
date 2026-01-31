"""Pytest configuration and shared fixtures."""

import logging

import pytest
from dotenv import load_dotenv

# Load environment variables from .env file for integration tests
load_dotenv()


@pytest.fixture(autouse=True)
def configure_logging():
    """Configure logging for tests."""
    logging.basicConfig(
        level=logging.WARNING,  # Reduce noise during tests
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers",
        "integration: mark test as integration test (requires real API keys)",
    )


# Common fixtures for agent tests
@pytest.fixture(autouse=True)
def mock_gemini_model(request, mocker):
    """Mock the Gemini model setting for non-integration tests."""
    # Skip for integration tests
    if "integration" in request.keywords:
        return None

    mocker.patch(
        "src.venue_recommendation_agent.search_agent.settings.gemini_model",
        "gemini-2.5-flash-lite",
    )
    mocker.patch(
        "src.venue_recommendation_agent.recommendation_agent.settings.gemini_model",
        "gemini-2.5-flash-lite",
    )
    return "gemini-2.5-flash-lite"


@pytest.fixture(autouse=True)
def mock_yelp_api_key(request, mocker):
    """Mock the Yelp API key setting for non-integration tests."""
    # Skip for integration tests
    if "integration" in request.keywords:
        return None

    mocker.patch("src.mcp_server.server.settings.yelp_api_key", "test_key")
    return "test_key"


@pytest.fixture
def yelp_client():
    """Create a YelpClient instance for testing."""
    from src.mcp_server.yelp.client import YelpClient

    return YelpClient(api_key="test_api_key_123")


@pytest.fixture
def mock_yelp_client(mocker):
    """Create a mocked YelpClient with async context manager support.

    Returns empty search results by default.
    """
    from src.mcp_server.yelp.models import SearchResponse

    mock_client = mocker.AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    # Return proper SearchResponse object with empty results
    mock_client.search_businesses.return_value = SearchResponse(businesses=[], total=0)

    mocker.patch(
        "src.mcp_server.server.YelpClient",
        return_value=mock_client,
    )
    return mock_client


@pytest.fixture
def sample_business():
    """Create a sample Business object for testing."""
    from src.mcp_server.yelp.models import Business, Category, Coordinates, Location

    return Business(
        id="test-restaurant-1",
        alias="test-restaurant-london",
        name="Test Restaurant",
        rating=4.5,
        review_count=100,
        price="££",
        location=Location(
            address1="123 Test St",
            city="London",
            country="UK",
            display_address=["123 Test St", "London", "UK"],
        ),
        categories=[Category(alias="italian", title="Italian")],
        coordinates=Coordinates(latitude=51.5074, longitude=-0.1278),
        distance=500.0,
        display_phone="+44 20 1234 5678",
        url="https://yelp.com/test",
        image_url="https://yelp.com/test.jpg",
        is_closed=False,
        transactions=["delivery"],
    )


@pytest.fixture
def sample_search_response(sample_business):
    """Create a sample SearchResponse with one business."""
    from src.mcp_server.yelp.models import SearchResponse

    return SearchResponse(businesses=[sample_business], total=1)
