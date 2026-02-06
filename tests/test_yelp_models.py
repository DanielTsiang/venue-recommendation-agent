"""Unit tests for Yelp API Pydantic models."""

import pytest

from src.mcp_server.yelp.models import (
    Attributes,
    Business,
    BusinessHours,
    Category,
    Coordinates,
    Location,
    OpenSlot,
    Region,
    RegionCenter,
    SearchResponse,
)


class TestOpenSlot:
    """Test suite for OpenSlot model."""

    def test_open_slot_creation(self):
        """Test OpenSlot can be created with required fields."""
        # When: OpenSlot is created
        slot = OpenSlot(start="0900", end="1700", day=0)

        # Then: Should have correct values
        assert slot.start == "0900"
        assert slot.end == "1700"
        assert slot.day == 0
        assert slot.is_overnight is False

    def test_open_slot_overnight(self):
        """Test OpenSlot with overnight hours."""
        # When: OpenSlot is created with overnight hours
        slot = OpenSlot(is_overnight=True, start="2200", end="0200", day=4)

        # Then: Should have overnight flag set
        assert slot.is_overnight is True
        assert slot.start == "2200"
        assert slot.end == "0200"


class TestBusinessHours:
    """Test suite for BusinessHours model."""

    def test_business_hours_creation(self):
        """Test BusinessHours can be created with open slots."""
        # Given: Open slots for a day
        slots = [
            OpenSlot(start="0900", end="1200", day=0),
            OpenSlot(start="1300", end="1700", day=0),
        ]

        # When: BusinessHours is created
        hours = BusinessHours(open=slots, hours_type="REGULAR", is_open_now=True)

        # Then: Should have correct values
        assert len(hours.open) == 2
        assert hours.hours_type == "REGULAR"
        assert hours.is_open_now is True

    def test_business_hours_defaults(self):
        """Test BusinessHours has sensible defaults."""
        # When: BusinessHours is created with no arguments
        hours = BusinessHours()

        # Then: Should have default values
        assert hours.open == []
        assert hours.hours_type == "REGULAR"
        assert hours.is_open_now is False


class TestAttributes:
    """Test suite for Attributes model."""

    def test_attributes_with_menu_url(self):
        """Test Attributes with menu_url set."""
        # When: Attributes is created with menu URL
        attrs = Attributes(menu_url="https://example.com/menu")

        # Then: Should have menu URL
        assert attrs.menu_url == "https://example.com/menu"
        assert attrs.waitlist_reservation is None

    def test_attributes_with_waitlist(self):
        """Test Attributes with waitlist_reservation set."""
        # When: Attributes is created with waitlist
        attrs = Attributes(waitlist_reservation=True)

        # Then: Should have waitlist flag
        assert attrs.waitlist_reservation is True

    def test_attributes_all_none(self):
        """Test Attributes with all None values."""
        # When: Attributes is created with no arguments
        attrs = Attributes()

        # Then: All fields should be None
        assert attrs.business_temp_closed is None
        assert attrs.menu_url is None
        assert attrs.open24_hours is None
        assert attrs.waitlist_reservation is None


class TestBusinessHelperMethods:
    """Test suite for Business helper methods."""

    @pytest.fixture
    def sample_business(self):
        """Create a sample business for testing."""
        return Business(
            id="test-123",
            alias="test-restaurant",
            name="Test Restaurant",
            url="https://yelp.com/test",
            rating=4.5,
            review_count=100,
            price="££",
            coordinates=Coordinates(latitude=51.5, longitude=-0.1),
            location=Location(
                address1="123 Test St",
                city="London",
                display_address=["123 Test St", "London", "UK"],
            ),
            categories=[
                Category(alias="italian", title="Italian"),
                Category(alias="pizza", title="Pizza"),
            ],
            business_hours=[
                BusinessHours(
                    open=[OpenSlot(start="0900", end="2200", day=0)],
                    is_open_now=True,
                )
            ],
            attributes=Attributes(
                menu_url="https://example.com/menu",
                waitlist_reservation=True,
            ),
        )

    def test_get_price_level(self, sample_business):
        """Test get_price_level returns correct numeric value."""
        # Then: Price level should be 2 for "££"
        assert sample_business.get_price_level() == 2

    def test_get_price_level_none(self):
        """Test get_price_level returns 0 when price is None."""
        # Given: Business with no price
        business = Business(
            id="test",
            alias="test",
            name="Test",
            url="https://yelp.com",
            coordinates=Coordinates(latitude=0, longitude=0),
            location=Location(),
        )

        # Then: Price level should be 0
        assert business.get_price_level() == 0

    def test_get_categories_str(self, sample_business):
        """Test get_categories_str returns comma-separated titles."""
        # Then: Should return comma-separated category titles
        assert sample_business.get_categories_str() == "Italian, Pizza"

    def test_get_address_str(self, sample_business):
        """Test get_address_str returns formatted address."""
        # Then: Should return comma-separated address parts
        assert sample_business.get_address_str() == "123 Test St, London, UK"

    def test_is_open_now_true(self, sample_business):
        """Test is_open_now returns True when business is open."""
        # Then: Should return True (business_hours[0].is_open_now = True)
        assert sample_business.is_open_now() is True

    def test_is_open_now_false(self):
        """Test is_open_now returns False when business is closed."""
        # Given: Business with is_open_now=False
        business = Business(
            id="test",
            alias="test",
            name="Test",
            url="https://yelp.com",
            coordinates=Coordinates(latitude=0, longitude=0),
            location=Location(),
            business_hours=[BusinessHours(is_open_now=False)],
        )

        # Then: Should return False
        assert business.is_open_now() is False

    def test_is_open_now_no_hours(self):
        """Test is_open_now returns False when no business hours."""
        # Given: Business with no business hours
        business = Business(
            id="test",
            alias="test",
            name="Test",
            url="https://yelp.com",
            coordinates=Coordinates(latitude=0, longitude=0),
            location=Location(),
        )

        # Then: Should return False
        assert business.is_open_now() is False

    def test_get_menu_url(self, sample_business):
        """Test get_menu_url returns menu URL when available."""
        # Then: Should return the menu URL
        assert sample_business.get_menu_url() == "https://example.com/menu"

    def test_get_menu_url_none(self):
        """Test get_menu_url returns None when no attributes."""
        # Given: Business with no attributes
        business = Business(
            id="test",
            alias="test",
            name="Test",
            url="https://yelp.com",
            coordinates=Coordinates(latitude=0, longitude=0),
            location=Location(),
        )

        # Then: Should return None
        assert business.get_menu_url() is None


class TestRegion:
    """Test suite for Region model."""

    def test_region_creation(self):
        """Test Region can be created with center coordinates."""
        # When: Region is created
        region = Region(center=RegionCenter(latitude=51.5, longitude=-0.1))

        # Then: Should have correct center coordinates
        assert region.center.latitude == 51.5
        assert region.center.longitude == -0.1


class TestSearchResponse:
    """Test suite for SearchResponse model."""

    def test_search_response_with_businesses(self):
        """Test SearchResponse can contain businesses."""
        # Given: A business
        business = Business(
            id="test",
            alias="test",
            name="Test Restaurant",
            url="https://yelp.com",
            coordinates=Coordinates(latitude=51.5, longitude=-0.1),
            location=Location(city="London"),
        )

        # When: SearchResponse is created
        response = SearchResponse(
            businesses=[business],
            total=100,
            region=Region(center=RegionCenter(latitude=51.5, longitude=-0.1)),
        )

        # Then: Should have correct values
        assert len(response.businesses) == 1
        assert response.businesses[0].name == "Test Restaurant"
        assert response.total == 100
        assert response.region.center.latitude == 51.5

    def test_search_response_empty(self):
        """Test SearchResponse with no businesses."""
        # When: Empty SearchResponse is created
        response = SearchResponse()

        # Then: Should have defaults
        assert response.businesses == []
        assert response.total == 0
        assert response.region is None
