"""TripAdvisor activity tool."""

from langchain.tools import tool

from Integrations.activity_client import ActivityClient

activity_client = ActivityClient()


@tool
async def search_activities(
    query: str,
    location: str | None = None,
):
    """
    Search TripAdvisor destinations and attractions.

    Args:
        query: Place or attraction to search.
        location: Optional city or country.

    Returns:
        List of matching places.
    """
    results = await activity_client.search_places(
        query=query,
        location=location,
    )

    return [place.model_dump() for place in results]


@tool
async def get_activity_details(
    place_id: str,
):
    """
    Retrieve detailed TripAdvisor information for a place.

    Args:
        place_id: TripAdvisor place identifier.

    Returns:
        Destination or attraction details.
    """
    details = await activity_client.get_place_details(
        place_id=place_id,
    )

    return details.model_dump()