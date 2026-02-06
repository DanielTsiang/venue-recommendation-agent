"""Simplified Pydantic schemas for search agent structured output.

These schemas are optimised for token efficiency while retaining all
essential data for venue recommendations. Verbose fields are excluded.
"""

from pydantic import BaseModel, Field


class CategoryOutput(BaseModel):
    """Simplified category - title only."""

    title: str = Field(description="Category display name (e.g., 'Italian', 'Pizza')")


class LocationOutput(BaseModel):
    """Business location information."""

    address1: str | None = Field(default=None, description="Street address line 1")
    address2: str | None = Field(default=None, description="Street address line 2")
    address3: str | None = Field(default=None, description="Street address line 3")
    city: str | None = Field(default=None, description="City name")
    zip_code: str | None = Field(default=None, description="Postal/ZIP code")
    country: str | None = Field(default=None, description="Country code")
    state: str | None = Field(default=None, description="State/region code")
    display_address: list[str] = Field(
        default_factory=list,
        description="Formatted address lines",
    )


class OpenSlotOutput(BaseModel):
    """Opening time slot."""

    is_overnight: bool = Field(default=False, description="Whether slot spans midnight")
    start: str = Field(description="Opening time in HHMM format")
    end: str = Field(description="Closing time in HHMM format")
    day: int = Field(description="Day of week (0=Monday, 6=Sunday)")


class BusinessHoursOutput(BaseModel):
    """Business opening hours with full schedule."""

    open: list[OpenSlotOutput] = Field(
        default_factory=list,
        description="Opening time slots",
    )
    hours_type: str = Field(default="REGULAR", description="Type of hours")
    is_open_now: bool = Field(default=False, description="Whether currently open")


class AttributesOutput(BaseModel):
    """Business attributes relevant for recommendations."""

    menu_url: str | None = Field(default=None, description="Link to menu")
    waitlist_reservation: bool | None = Field(
        default=None,
        description="Whether reservations available",
    )


class BusinessOutput(BaseModel):
    """Simplified business for recommendations.

    Excludes verbose fields:
    - id (name is sufficient for display)
    - alias (redundant with name)
    - url (long Yelp tracking URL)
    - image_url (S3 URL not needed for text)
    - coordinates (have display_address instead)
    - transactions (usually empty)
    """

    name: str = Field(description="Business name")
    rating: float = Field(default=0.0, description="Rating out of 5")
    review_count: int = Field(default=0, description="Number of reviews")
    price: str | None = Field(default=None, description="Price level (£ to ££££)")
    distance: float | None = Field(default=None, description="Distance in meters")
    is_closed: bool = Field(default=False, description="Permanently closed")
    categories: list[CategoryOutput] = Field(
        default_factory=list,
        description="Business categories",
    )
    location: LocationOutput = Field(
        default_factory=LocationOutput,
        description="Business location",
    )
    display_phone: str | None = Field(default=None, description="Formatted phone")
    business_hours: list[BusinessHoursOutput] = Field(
        default_factory=list,
        description="Opening hours",
    )
    attributes: AttributesOutput | None = Field(
        default=None,
        description="Business attributes",
    )

    def get_address_str(self) -> str:
        """Get formatted address string."""
        return ", ".join(self.location.display_address)

    def is_open_now(self) -> bool:
        """Check if business is currently open."""
        if self.business_hours:
            return self.business_hours[0].is_open_now
        return False


class SearchAgentOutput(BaseModel):
    """Simplified search response for agent output.

    This schema is optimised for token efficiency while retaining all data needed for recommendations.
    """

    businesses: list[BusinessOutput] = Field(
        default_factory=list,
        description="List of matching businesses",
    )
    total: int = Field(default=0, description="Total matching businesses")
