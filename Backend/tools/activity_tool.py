"""TripAdvisor activity tool."""

from langchain_core.tools import tool

from Backend.Exceptions.exception import ActivityAPIError
from Backend.integrations.activity_client import activity_client
from Backend.Logger.decorators import log_tool
from Backend.Logger.logger import get_logger


logger = get_logger(__name__)


@tool
@log_tool("search_activities")
async def search_activities(
    query: str,
    location: str | None = None,
) -> list[dict]:
    """
    Search TripAdvisor for attractions, museums, landmarks,
    restaurants, parks, and other places of interest.

    Args:
        query:
            Search keyword or attraction name.

        location:
            Optional city, region, or country used to narrow
            the search.

    Returns:
        List of matching places as JSON-compatible dictionaries.
    """

    try:
        places = await activity_client.search_places(
            query=query,
            location=location,
        )

        return [
            place.model_dump(mode="json")
            for place in places
        ]

    except ActivityAPIError:
        logger.exception(
            "Activity search failed."
        )
        raise