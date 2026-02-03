"""Unit tests for Yelp API client."""

import httpx
import pytest

from src.mcp_server.exceptions import (
    YelpAPIError,
    YelpAuthError,
    YelpRateLimitError,
)
from src.mcp_server.yelp.client import YelpClient
from src.mcp_server.yelp.models import SearchResponse


@pytest.fixture
def mock_httpx_client(mocker):
    """Fixture to create a mocked httpx.AsyncClient."""
    mock_client = mocker.AsyncMock(spec=httpx.AsyncClient)
    return mock_client


@pytest.fixture
def yelp_client():
    """Fixture to create a YelpClient instance."""
    return YelpClient(api_key="test_api_key_123")


class TestYelpClient:
    """Test suite for YelpClient."""

    async def test_context_manager_initialises_client(self, mocker):
        """Test async context manager initialises httpx client."""
        # Given: A YelpClient instance
        client = YelpClient(api_key="test_key")
        mock_async_client = mocker.patch("httpx.AsyncClient", autospec=True)

        # When: Context manager is entered
        async with client:
            # Then: httpx.AsyncClient should be initialised
            mock_async_client.assert_called_once_with(
                base_url="https://api.yelp.com/v3",
                headers={
                    "Authorization": "Bearer test_key",
                    "Accept": "application/json",
                },
                timeout=30.0,
            )

    async def test_search_businesses_success(self, yelp_client, mocker):
        """Test successful business search."""
        # Given: A mocked successful API response
        mock_response = mocker.Mock()
        mock_response.json.return_value = {
            "businesses": [
                {
                    "id": "business1",
                    "alias": "test-restaurant-london",
                    "name": "Test Restaurant",
                    "rating": 4.5,
                    "review_count": 100,
                    "price": "££",
                    "url": "https://yelp.com/test-restaurant",
                    "location": {
                        "address1": "123 Test St",
                        "city": "London",
                        "country": "UK",
                    },
                    "categories": [{"alias": "italian", "title": "Italian"}],
                    "coordinates": {"latitude": 51.5074, "longitude": -0.1278},
                    "distance": 500.0,
                }
            ],
            "total": 1,
        }

        mock_client = mocker.AsyncMock()
        mock_client.get.return_value = mock_response
        yelp_client._client = mock_client

        # When: search_businesses is called
        result = await yelp_client.search_businesses(
            location="London, UK",
            term="restaurants",
            limit=20,
        )

        # Then: Result should be a SearchResponse with correct data
        assert isinstance(result, SearchResponse)
        assert len(result.businesses) == 1
        assert result.businesses[0].name == "Test Restaurant"
        assert result.businesses[0].rating == 4.5
        assert result.total == 1

        # And: API should be called with correct parameters
        mock_client.get.assert_called_once_with(
            "/businesses/search",
            params={
                "location": "London, UK",
                "term": "restaurants",
                "limit": 20,
                "sort_by": "best_match",
            },
        )

    async def test_search_businesses_with_all_parameters(self, yelp_client, mocker):
        """Test business search with all optional parameters."""
        # Given: A mocked successful API response
        mock_response = mocker.Mock()
        mock_response.json.return_value = {"businesses": [], "total": 0}

        mock_client = mocker.AsyncMock()
        mock_client.get.return_value = mock_response
        yelp_client._client = mock_client

        # When: search_businesses is called with all parameters
        await yelp_client.search_businesses(
            location="London, UK",
            term="coffee",
            categories="cafes,coffee",
            price="1,2",
            radius=1000,
            limit=10,
            sort_by="rating",
            open_now=True,
        )

        # Then: API should be called with all parameters
        mock_client.get.assert_called_once_with(
            "/businesses/search",
            params={
                "location": "London, UK",
                "term": "coffee",
                "categories": "cafes,coffee",
                "price": "1,2",
                "radius": 1000,
                "limit": 10,
                "sort_by": "rating",
                "open_now": "true",
            },
        )

    async def test_search_businesses_enforces_max_limit(self, yelp_client, mocker):
        """Test search_businesses enforces Yelp's max limit of 50."""
        # Given: A mocked successful API response
        mock_response = mocker.Mock()
        mock_response.json.return_value = {"businesses": [], "total": 0}

        mock_client = mocker.AsyncMock()
        mock_client.get.return_value = mock_response
        yelp_client._client = mock_client

        # When: search_businesses is called with limit > 50
        await yelp_client.search_businesses(location="London, UK", limit=100)

        # Then: Limit should be capped at 50
        call_args = mock_client.get.call_args
        assert call_args[1]["params"]["limit"] == 50

    async def test_search_businesses_enforces_max_radius(self, yelp_client, mocker):
        """Test search_businesses enforces Yelp's max radius of 40000m."""
        # Given: A mocked successful API response
        mock_response = mocker.Mock()
        mock_response.json.return_value = {"businesses": [], "total": 0}

        mock_client = mocker.AsyncMock()
        mock_client.get.return_value = mock_response
        yelp_client._client = mock_client

        # When: search_businesses is called with radius > 40000
        await yelp_client.search_businesses(location="London, UK", radius=50000)

        # Then: Radius should be capped at 40000
        call_args = mock_client.get.call_args
        assert call_args[1]["params"]["radius"] == 40000

    async def test_search_businesses_raises_auth_error_on_401(
        self, yelp_client, mocker
    ):
        """Test search_businesses raises YelpAuthError on 401."""
        # Given: A mocked 401 Unauthorized response
        mock_response = mocker.Mock()
        mock_response.status_code = 401

        mock_client = mocker.AsyncMock()
        mock_client.get.side_effect = httpx.HTTPStatusError(
            "Unauthorized", request=mocker.Mock(), response=mock_response
        )
        yelp_client._client = mock_client

        # When: search_businesses is called
        # Then: YelpAuthError should be raised
        with pytest.raises(YelpAuthError, match="Invalid Yelp API key"):
            await yelp_client.search_businesses(location="London, UK")

    async def test_search_businesses_raises_rate_limit_error_on_429(
        self, yelp_client, mocker
    ):
        """Test search_businesses raises YelpRateLimitError on 429."""
        # Given: A mocked 429 Rate Limit response
        mock_response = mocker.Mock()
        mock_response.status_code = 429

        mock_client = mocker.AsyncMock()
        mock_client.get.side_effect = httpx.HTTPStatusError(
            "Rate Limited", request=mocker.Mock(), response=mock_response
        )
        yelp_client._client = mock_client

        # When: search_businesses is called
        # Then: YelpRateLimitError should be raised
        with pytest.raises(YelpRateLimitError, match="Yelp API rate limit exceeded"):
            await yelp_client.search_businesses(location="London, UK")

    async def test_search_businesses_raises_api_error_on_400(self, yelp_client, mocker):
        """Test search_businesses raises YelpAPIError on 400 with error message."""
        # Given: A mocked 400 Bad Request response
        mock_response = mocker.Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "error": {"description": "Invalid location parameter"}
        }

        mock_client = mocker.AsyncMock()
        mock_client.get.side_effect = httpx.HTTPStatusError(
            "Bad Request", request=mocker.Mock(), response=mock_response
        )
        yelp_client._client = mock_client

        # When: search_businesses is called
        # Then: YelpAPIError should be raised with error description
        with pytest.raises(
            YelpAPIError, match="Bad request: Invalid location parameter"
        ):
            await yelp_client.search_businesses(location="")

    async def test_search_businesses_raises_api_error_on_timeout(
        self, yelp_client, mocker
    ):
        """Test search_businesses raises YelpAPIError on timeout."""
        # Given: A mocked timeout exception
        mock_client = mocker.AsyncMock()
        mock_client.get.side_effect = httpx.TimeoutException("Request timed out")
        yelp_client._client = mock_client

        # When: search_businesses is called
        # Then: YelpAPIError should be raised
        with pytest.raises(YelpAPIError, match="Yelp API request timed out"):
            await yelp_client.search_businesses(location="London, UK")

    async def test_search_businesses_raises_api_error_on_network_error(
        self, yelp_client, mocker
    ):
        """Test search_businesses raises YelpAPIError on network error."""
        # Given: A mocked network error
        mock_client = mocker.AsyncMock()
        mock_client.get.side_effect = httpx.RequestError("Network error")
        yelp_client._client = mock_client

        # When: search_businesses is called
        # Then: YelpAPIError should be raised
        with pytest.raises(YelpAPIError, match="Network error"):
            await yelp_client.search_businesses(location="London, UK")

    async def test_search_businesses_raises_runtime_error_if_not_initialised(
        self, yelp_client
    ):
        """Test search_businesses raises RuntimeError if client not initialised."""
        # Given: YelpClient without initialised httpx client
        # (yelp_client._client is None by default)

        # When: search_businesses is called without context manager
        # Then: RuntimeError should be raised
        with pytest.raises(RuntimeError, match="Client not initialised"):
            await yelp_client.search_businesses(location="London, UK")
