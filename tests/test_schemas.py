"""Unit tests for search agent output schemas."""

from src.venue_recommendation_agent.schemas import (
    AttributesOutput,
    BusinessHoursOutput,
    BusinessOutput,
    CategoryOutput,
    LocationOutput,
    OpenSlotOutput,
    SearchAgentOutput,
)


class TestBusinessOutput:
    """Test suite for BusinessOutput model."""

    def test_get_address_str_joins_lines(self):
        """Test get_address_str joins display_address lines with comma."""
        # Given: Business with multi-line address
        business = BusinessOutput(
            name="Test Restaurant",
            location=LocationOutput(
                display_address=["123 Main St", "London", "EC1A 1BB"]
            ),
        )

        # When: Getting address string
        result = business.get_address_str()

        # Then: Should join with comma separator
        assert result == "123 Main St, London, EC1A 1BB"

    def test_get_address_str_empty(self):
        """Test get_address_str handles empty address."""
        # Given: Business with empty address
        business = BusinessOutput(name="Test Restaurant")

        # When: Getting address string
        result = business.get_address_str()

        # Then: Should return empty string
        assert result == ""

    def test_is_open_now_true(self):
        """Test is_open_now returns True when business is open."""
        # Given: Business with hours showing open
        business = BusinessOutput(
            name="Test Restaurant",
            business_hours=[
                BusinessHoursOutput(
                    is_open_now=True,
                    open=[OpenSlotOutput(start="0900", end="2200", day=0)],
                )
            ],
        )

        # When: Checking if open
        result = business.is_open_now()

        # Then: Should return True
        assert result is True

    def test_is_open_now_false(self):
        """Test is_open_now returns False when business is closed."""
        # Given: Business with hours showing closed
        business = BusinessOutput(
            name="Test Restaurant",
            business_hours=[
                BusinessHoursOutput(
                    is_open_now=False,
                    open=[OpenSlotOutput(start="0900", end="2200", day=0)],
                )
            ],
        )

        # When: Checking if open
        result = business.is_open_now()

        # Then: Should return False
        assert result is False

    def test_is_open_now_no_hours(self):
        """Test is_open_now returns False when no hours available."""
        # Given: Business without hours
        business = BusinessOutput(name="Test Restaurant")

        # When: Checking if open
        result = business.is_open_now()

        # Then: Should return False (unknown defaults to closed)
        assert result is False

    def test_business_defaults(self):
        """Test BusinessOutput has sensible defaults."""
        # When: Creating business with only required field
        business = BusinessOutput(name="Minimal Restaurant")

        # Then: Should have default values
        assert business.name == "Minimal Restaurant"
        assert business.rating == 0.0
        assert business.review_count == 0
        assert business.price is None
        assert business.distance is None
        assert business.is_closed is False
        assert business.categories == []
        assert business.display_phone is None
        assert business.business_hours == []
        assert business.attributes is None


class TestSearchAgentOutput:
    """Test suite for SearchAgentOutput model."""

    def test_search_agent_output_with_businesses(self):
        """Test SearchAgentOutput with business list."""
        # Given: Business list
        businesses = [
            BusinessOutput(name="Restaurant 1", rating=4.5),
            BusinessOutput(name="Restaurant 2", rating=4.0),
        ]

        # When: Creating search output
        output = SearchAgentOutput(businesses=businesses, total=2)

        # Then: Should contain businesses
        assert len(output.businesses) == 2
        assert output.total == 2
        assert output.businesses[0].name == "Restaurant 1"

    def test_search_agent_output_defaults(self):
        """Test SearchAgentOutput defaults to empty."""
        # When: Creating empty output
        output = SearchAgentOutput()

        # Then: Should have empty defaults
        assert output.businesses == []
        assert output.total == 0


class TestSupportingModels:
    """Test suite for supporting output models."""

    def test_category_output(self):
        """Test CategoryOutput creation."""
        category = CategoryOutput(title="Italian")
        assert category.title == "Italian"

    def test_location_output_defaults(self):
        """Test LocationOutput defaults."""
        location = LocationOutput()
        assert location.address1 is None
        assert location.address2 is None
        assert location.address3 is None
        assert location.city is None
        assert location.zip_code is None
        assert location.country is None
        assert location.state is None
        assert location.display_address == []

    def test_location_output_full(self):
        """Test LocationOutput with all fields."""
        location = LocationOutput(
            address1="123 Main St",
            address2="Floor 2",
            address3=None,
            city="London",
            zip_code="EC1A 1BB",
            country="GB",
            state=None,
            display_address=["123 Main St", "Floor 2", "London EC1A 1BB"],
        )
        assert location.address1 == "123 Main St"
        assert location.address2 == "Floor 2"
        assert location.city == "London"
        assert location.zip_code == "EC1A 1BB"
        assert location.country == "GB"
        assert len(location.display_address) == 3

    def test_open_slot_output(self):
        """Test OpenSlotOutput creation."""
        slot = OpenSlotOutput(start="0900", end="2200", day=1)
        assert slot.is_overnight is False
        assert slot.start == "0900"
        assert slot.end == "2200"
        assert slot.day == 1

    def test_open_slot_output_overnight(self):
        """Test OpenSlotOutput with overnight hours."""
        slot = OpenSlotOutput(is_overnight=True, start="2200", end="0200", day=5)
        assert slot.is_overnight is True
        assert slot.start == "2200"
        assert slot.end == "0200"
        assert slot.day == 5

    def test_business_hours_output_defaults(self):
        """Test BusinessHoursOutput defaults."""
        hours = BusinessHoursOutput()
        assert hours.open == []
        assert hours.hours_type == "REGULAR"
        assert hours.is_open_now is False

    def test_attributes_output(self):
        """Test AttributesOutput creation."""
        attrs = AttributesOutput(
            menu_url="https://example.com/menu",
            waitlist_reservation=True,
        )
        assert attrs.menu_url == "https://example.com/menu"
        assert attrs.waitlist_reservation is True

    def test_attributes_output_defaults(self):
        """Test AttributesOutput defaults to None."""
        attrs = AttributesOutput()
        assert attrs.menu_url is None
        assert attrs.waitlist_reservation is None
