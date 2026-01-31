"""Yelp API client for business search."""

import logging

import httpx
from tenacity import (
    retry,
    retry_if_exception,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.mcp_server.exceptions import YelpAPIError, YelpAuthError, YelpRateLimitError
from src.mcp_server.yelp.models import SearchResponse

logger = logging.getLogger(__name__)


def _is_retryable_http_error(exception: BaseException) -> bool:
    """Check if HTTP error is retryable (5xx errors only).

    Args:
        exception: Exception to check

    Returns:
        True if exception is a retryable HTTP error
    """
    if isinstance(exception, httpx.HTTPStatusError):
        # Retry on server errors (500, 502, 503, 504)
        return exception.response.status_code >= 500
    return False


class YelpClient:
    """Async client for Yelp Fusion API."""

    BASE_URL = "https://api.yelp.com/v3"
    TIMEOUT = 30.0

    def __init__(self, api_key: str):
        """Initialise Yelp client with API key.

        Args:
            api_key: Yelp API key from https://www.yelp.com/developers
        """
        self.api_key = api_key
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self):
        """Async context manager entry."""
        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Accept": "application/json",
            },
            timeout=self.TIMEOUT,
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=(
            retry_if_exception_type(httpx.TimeoutException)
            | retry_if_exception_type(httpx.NetworkError)
            | retry_if_exception_type(httpx.ConnectError)
            | retry_if_exception(_is_retryable_http_error)
        ),
        reraise=True,
    )
    async def search_businesses(
        self,
        location: str,
        term: str | None = None,
        categories: str | None = None,
        price: str | None = None,
        radius: int | None = None,
        limit: int = 20,
        sort_by: str = "best_match",
        open_now: bool | None = None,
    ) -> SearchResponse:
        """Search for businesses on Yelp.

        Automatically retries on transient failures (network errors, timeouts, 5xx errors)
        with exponential backoff (max 3 attempts).

        Args:
            location: Location to search (e.g., "London, UK", "10 Downing St, London")
            term: Search term (e.g., "restaurants", "coffee")
            categories: Comma-separated Yelp category aliases
            price: Price levels as comma-separated string (e.g., "1,2,3,4")
            radius: Search radius in meters (max 40000)
            limit: Number of results to return (default 20, max 50)
            sort_by: Sort order ("best_match", "rating", "review_count", "distance")
            open_now: Filter to businesses open now

        Returns:
            SearchResponse containing list of businesses

        Raises:
            YelpAuthError: Invalid API key (401)
            YelpRateLimitError: Rate limit exceeded (429)
            YelpAPIError: Other API errors
        """
        if not self._client:
            raise RuntimeError("Client not initialised. Use async context manager.")

        # Build query parameters
        params = {
            "location": location,
            "limit": min(limit, 50),  # Yelp max is 50
            "sort_by": sort_by,
        }

        if term:
            params["term"] = term
        if categories:
            params["categories"] = categories
        if price:
            params["price"] = price
        if radius:
            params["radius"] = min(radius, 40000)  # Yelp max is 40000 meters
        if open_now is not None:
            params["open_now"] = str(open_now).lower()

        try:
            logger.info(
                f"Searching Yelp: location={location}, term={term}, limit={limit}"
            )
            response = await self._client.get("/businesses/search", params=params)
            response.raise_for_status()

            data = response.json()
            logger.info(f"Yelp returned {len(data.get('businesses', []))} businesses")

            return SearchResponse(**data)

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise YelpAuthError("Invalid Yelp API key") from e
            elif e.response.status_code == 429:
                raise YelpRateLimitError("Yelp API rate limit exceeded") from e
            elif e.response.status_code == 400:
                error_msg = (
                    e.response.json().get("error", {}).get("description", str(e))
                )
                raise YelpAPIError(f"Bad request: {error_msg}") from e
            else:
                raise YelpAPIError(f"Yelp API error: {e}") from e

        except httpx.TimeoutException as e:
            raise YelpAPIError("Yelp API request timed out") from e

        except httpx.RequestError as e:
            raise YelpAPIError(f"Network error: {e}") from e

        except Exception as e:
            logger.error(f"Unexpected error in Yelp API call: {e}")
            raise YelpAPIError(f"Unexpected error: {e}") from e
