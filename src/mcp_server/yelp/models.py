"""Pydantic models for Yelp API responses."""

from pydantic import BaseModel, Field


class Coordinates(BaseModel):
    """Geographic coordinates."""

    latitude: float
    longitude: float


class Location(BaseModel):
    """Business location information."""

    address1: str | None = None
    address2: str | None = None
    address3: str | None = None
    city: str | None = None
    zip_code: str | None = None
    country: str | None = None
    state: str | None = None
    display_address: list[str] = Field(default_factory=list)


class Category(BaseModel):
    """Business category."""

    alias: str
    title: str


class Business(BaseModel):
    """Business information from Yelp API."""

    id: str
    alias: str
    name: str
    image_url: str | None = None
    is_closed: bool = False
    url: str
    review_count: int = 0
    categories: list[Category] = Field(default_factory=list)
    rating: float = 0.0
    coordinates: Coordinates
    transactions: list[str] = Field(default_factory=list)
    price: str | None = None
    location: Location
    phone: str | None = None
    display_phone: str | None = None
    distance: float | None = None

    def get_price_level(self) -> int:
        """Get numeric price level (1-4)."""
        return len(self.price) if self.price else 0

    def get_categories_str(self) -> str:
        """Get comma-separated category names."""
        return ", ".join(cat.title for cat in self.categories)

    def get_address_str(self) -> str:
        """Get formatted address string."""
        return ", ".join(self.location.display_address)


class SearchResponse(BaseModel):
    """Response from Yelp Business Search API."""

    businesses: list[Business] = Field(default_factory=list)
    total: int = 0
    region: dict | None = None
