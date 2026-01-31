"""FastMCP server for Yelp Places API integration."""

import logging
import sys
from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from src.config import settings
from src.mcp_server.exceptions import YelpAPIError
from src.mcp_server.yelp.client import YelpClient
from src.mcp_server.yelp.models import SearchResponse

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)

# Initialise FastMCP server
mcp = FastMCP("Yelp Places Search")


@mcp.tool(
    description="Search for restaurants, cafés, bars, and other venues on Yelp. "
    "Returns businesses with name, rating, reviews, price, distance, address, phone, and more."
)
async def search_yelp_businesses(
    location: Annotated[
        str,
        Field(
            description='City, address, or neighborhood (e.g., "London", "Shoreditch, London")'
        ),
    ],
    term: Annotated[
        str | None,
        Field(
            description='Search term (e.g., "restaurants", "coffee", "italian food")'
        ),
    ] = None,
    categories: Annotated[
        str | None,
        Field(description="Comma-separated Yelp category aliases"),
    ] = None,
    price: Annotated[
        str | None,
        Field(description='Price levels "1,2,3,4" where 1=£, 2=££, 3=£££, 4=££££'),
    ] = None,
    radius: Annotated[
        int | None,
        Field(description="Search radius in meters (max 40000)"),
    ] = None,
    limit: Annotated[
        int,
        Field(description="Number of results to return (max 50)", ge=1, le=50),
    ] = 20,
    sort_by: Annotated[
        str,
        Field(
            description='Sort order: "best_match", "rating", "review_count", or "distance"'
        ),
    ] = "best_match",
    open_now: Annotated[
        bool | None,
        Field(description="Filter to only currently open businesses"),
    ] = None,
) -> dict:
    """Search for businesses on Yelp.

    Args:
        location: Location to search (city, address, or neighborhood)
        term: Search term (e.g., "restaurants", "coffee", "italian food")
        categories: Comma-separated Yelp category aliases
        price: Price levels (e.g., "1,2" for £ and ££)
        radius: Search radius in meters (max 40000)
        limit: Number of results (default 20, max 50)
        sort_by: Sort order ("best_match", "rating", "review_count", "distance")
        open_now: Filter to only open businesses

    Returns:
        Dictionary with businesses list, total count, and summary
    """
    logger.info(f"MCP tool called: search_yelp_businesses(location={location})")

    try:
        async with YelpClient(settings.yelp_api_key) as client:
            response: SearchResponse = await client.search_businesses(
                location=location,
                term=term,
                categories=categories,
                price=price,
                radius=radius,
                limit=limit,
                sort_by=sort_by,
                open_now=open_now,
            )

        # Convert to dictionary for MCP response
        businesses_data = []
        for business in response.businesses:
            business_dict = business.model_dump()
            # Add custom computed fields
            business_dict["price"] = business.price or "N/A"
            business_dict["distance_meters"] = (
                round(business.distance, 2) if business.distance else None
            )
            business_dict["distance_miles"] = (
                round(business.distance / 1609.34, 2) if business.distance else None
            )
            business_dict["categories"] = business.get_categories_str()
            business_dict["address"] = business.get_address_str()
            business_dict["phone"] = business.display_phone or business.phone or "N/A"
            businesses_data.append(business_dict)

        # Create summary
        summary = f"Found {len(businesses_data)} businesses"
        if len(businesses_data) > 0:
            avg_rating = sum(b["rating"] for b in businesses_data) / len(
                businesses_data
            )
            summary += f" (average rating: {avg_rating:.1f})"

        result = {
            "businesses": businesses_data,
            "total": response.total,
            "count": len(businesses_data),
            "summary": summary,
        }

        logger.info(
            f"Returning {len(businesses_data)} businesses for location: {location}"
        )
        return result

    except YelpAPIError as e:
        logger.error(f"Yelp API error: {e}")
        return {
            "businesses": [],
            "total": 0,
            "count": 0,
            "summary": f"Error: {str(e)}",
            "error": str(e),
        }

    except Exception as e:
        logger.error(f"Unexpected error in search_yelp_businesses: {e}")
        return {
            "businesses": [],
            "total": 0,
            "count": 0,
            "summary": f"Unexpected error: {str(e)}",
            "error": str(e),
        }


def main():
    """Run the FastMCP server."""
    logger.info("Starting Yelp Places MCP Server...")
    logger.info(f"Log level: {settings.log_level}")
    logger.info(f"Yelp API key configured: {bool(settings.yelp_api_key)}")

    # Run the server
    mcp.run()


if __name__ == "__main__":
    main()
