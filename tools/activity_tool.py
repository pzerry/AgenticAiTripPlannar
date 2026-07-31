"""TripAdvisor activity tool."""

from langchain.tools import tool

from integrations.activity_client import ActivityClient

activity_client = ActivityClient()


@tool
async def search_activities(
    query: str,
    location: str | None = None,
) -> list[dict]:
    """
    Search TripAdvisor for attractions, restaurants, museums,
    landmarks, and other places of interest.

    Args:
        query: Name or keyword of the place to search.
        location: Optional city, region, or country to narrow the search.

    Returns:
        A list of matching places with summary information.
    """

    places = await activity_client.search_places(
        query=query,
        location=location,
    )

    return [place.model_dump() for place in places]