"""Custom exceptions for Yelp API interactions."""


class YelpAPIError(Exception):
    """Base exception for Yelp API errors."""

    pass


class YelpAuthError(YelpAPIError):
    """Raised when Yelp API authentication fails (401)."""

    pass


class YelpRateLimitError(YelpAPIError):
    """Raised when Yelp API rate limit is exceeded (429)."""

    pass
