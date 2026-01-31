"""Unit tests for MCP server tools."""

import pytest

from src.mcp_server.exceptions import YelpAPIError, YelpAuthError
from src.mcp_server.server import search_yelp_businesses as _search_tool
from src.mcp_server.yelp.models import SearchResponse

search_yelp_businesses = _search_tool.fn


class TestSearchYelpBusinessesTool:
    """Test suite for search_yelp_businesses MCP tool."""

    async def test_search_yelp_businesses_success(self, sample_search_response, mocker):
        """Test search_yelp_businesses returns formatted results."""
        # Given: Mocked YelpClient with successful response (via fixtures)
        mock_client = mocker.AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.search_businesses.return_value = sample_search_response

        mocker.patch("src.mcp_server.server.YelpClient", return_value=mock_client)

        # When: search_yelp_businesses is called
        result = await search_yelp_businesses(location="London, UK", term="restaurants")

        # Then: Result should be properly formatted
        assert result["total"] == 1
        assert result["count"] == 1
        assert len(result["businesses"]) == 1
        assert "error" not in result

        # And: Business data should be correctly formatted
        business = result["businesses"][0]
        assert business["id"] == "test-restaurant-1"
        assert business["name"] == "Test Restaurant"
        assert business["rating"] == 4.5
        assert business["review_count"] == 100
        assert business["price"] == "££"
        assert business["distance_meters"] == 500.0
        assert business["distance_miles"] == pytest.approx(0.31, rel=0.01)
        assert business["categories"] == "Italian"
        assert "123 Test St" in business["address"]
        assert business["phone"] == "+44 20 1234 5678"
        assert business["is_closed"] is False

        # And: Summary should include average rating
        assert "Found 1 businesses" in result["summary"]
        assert "average rating: 4.5" in result["summary"]

    async def test_search_yelp_businesses_with_all_parameters(self, mock_yelp_client):
        """Test search_yelp_businesses passes all parameters to client."""
        # Given: Mocked YelpClient (via fixture)
        # When: search_yelp_businesses is called with all parameters
        await search_yelp_businesses(
            location="London, UK",
            term="coffee",
            categories="cafes,coffee",
            price="1,2",
            radius=1000,
            limit=10,
            sort_by="rating",
            open_now=True,
        )

        # Then: All parameters should be passed to client
        mock_yelp_client.search_businesses.assert_called_once_with(
            location="London, UK",
            term="coffee",
            categories="cafes,coffee",
            price="1,2",
            radius=1000,
            limit=10,
            sort_by="rating",
            open_now=True,
        )

    async def test_search_yelp_businesses_handles_missing_optional_fields(self, mocker):
        """Test search_yelp_businesses handles businesses with missing optional fields."""
        # Given: Business with minimal fields
        from src.mcp_server.yelp.models import Business, Coordinates, Location

        mock_business = Business(
            id="test-minimal",
            alias="test-minimal-london",
            name="Minimal Business",
            rating=3.5,
            review_count=10,
            price=None,
            location=Location(address1="", city="London", country="UK"),
            categories=[],
            coordinates=Coordinates(latitude=51.5074, longitude=-0.1278),
            distance=None,
            display_phone=None,
            phone=None,
            url="https://yelp.com/minimal",
            image_url=None,
            is_closed=False,
            transactions=[],
        )

        mock_response = SearchResponse(businesses=[mock_business], total=1)
        mock_client = mocker.AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.search_businesses.return_value = mock_response

        mocker.patch("src.mcp_server.server.YelpClient", return_value=mock_client)

        # When: search_yelp_businesses is called
        result = await search_yelp_businesses(location="London, UK")

        # Then: Should handle missing fields gracefully
        business = result["businesses"][0]
        assert business["price"] == "N/A"
        assert business["distance_meters"] is None
        assert business["distance_miles"] is None
        assert business["phone"] == "N/A"

    async def test_search_yelp_businesses_calculates_average_rating(self, mocker):
        """Test search_yelp_businesses calculates average rating correctly."""
        # Given: Multiple businesses with different ratings
        from src.mcp_server.yelp.models import Business, Coordinates, Location

        businesses = [
            Business(
                id=f"biz-{i}",
                alias=f"biz-{i}-london",
                name=f"Business {i}",
                rating=rating,
                review_count=10,
                url=f"https://yelp.com/biz-{i}",
                location=Location(city="London", country="UK"),
                categories=[],
                coordinates=Coordinates(latitude=51.5074, longitude=-0.1278),
            )
            for i, rating in enumerate([4.0, 4.5, 5.0])
        ]

        mock_response = SearchResponse(businesses=businesses, total=3)
        mock_client = mocker.AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.search_businesses.return_value = mock_response

        mocker.patch("src.mcp_server.server.YelpClient", return_value=mock_client)

        # When: search_yelp_businesses is called
        result = await search_yelp_businesses(location="London, UK")

        # Then: Average rating should be calculated correctly
        assert "average rating: 4.5" in result["summary"]

    async def test_search_yelp_businesses_handles_yelp_api_error(self, mocker):
        """Test search_yelp_businesses handles YelpAPIError gracefully."""
        # Given: YelpClient that raises YelpAPIError
        mock_client = mocker.AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.search_businesses.side_effect = YelpAPIError("API error occurred")

        mocker.patch("src.mcp_server.server.YelpClient", return_value=mock_client)

        # When: search_yelp_businesses is called
        result = await search_yelp_businesses(location="London, UK")

        # Then: Should return error response
        assert result["businesses"] == []
        assert result["total"] == 0
        assert result["count"] == 0
        assert "Error: API error occurred" in result["summary"]
        assert result["error"] == "API error occurred"

    async def test_search_yelp_businesses_handles_auth_error(self, mocker):
        """Test search_yelp_businesses handles YelpAuthError gracefully."""
        # Given: YelpClient that raises YelpAuthError
        mock_client = mocker.AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.search_businesses.side_effect = YelpAuthError("Invalid API key")

        mocker.patch("src.mcp_server.server.YelpClient", return_value=mock_client)

        # When: search_yelp_businesses is called
        result = await search_yelp_businesses(location="London, UK")

        # Then: Should return error response with auth error message
        assert result["businesses"] == []
        assert "Error: Invalid API key" in result["summary"]
        assert result["error"] == "Invalid API key"

    async def test_search_yelp_businesses_handles_unexpected_error(self, mocker):
        """Test search_yelp_businesses handles unexpected errors gracefully."""
        # Given: YelpClient that raises unexpected exception
        mock_client = mocker.AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.search_businesses.side_effect = RuntimeError("Unexpected error")

        mocker.patch("src.mcp_server.server.YelpClient", return_value=mock_client)

        # When: search_yelp_businesses is called
        result = await search_yelp_businesses(location="London, UK")

        # Then: Should return error response
        assert result["businesses"] == []
        assert "Unexpected error" in result["summary"]
        assert "error" in result

    async def test_search_yelp_businesses_logs_execution(
        self, mock_yelp_client, caplog
    ):
        """Test search_yelp_businesses logs tool execution."""
        # Given: Mocked YelpClient (via fixture)
        # When: search_yelp_businesses is called
        with caplog.at_level("INFO"):
            await search_yelp_businesses(location="London, UK")

        # Then: Should log tool invocation
        assert "MCP tool called: search_yelp_businesses" in caplog.text
        assert "location=London, UK" in caplog.text
        assert "Returning" in caplog.text

    async def test_search_yelp_businesses_empty_results(self, mock_yelp_client):
        """Test search_yelp_businesses handles empty results."""
        # Given: YelpClient returns no businesses (via fixture)
        # When: search_yelp_businesses is called
        result = await search_yelp_businesses(location="Unknown Location")

        # Then: Should return empty results without error
        assert result["businesses"] == []
        assert result["total"] == 0
        assert result["count"] == 0
        assert result["summary"] == "Found 0 businesses"
        assert "error" not in result
