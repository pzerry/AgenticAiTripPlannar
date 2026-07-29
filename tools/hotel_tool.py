"""Hotel search tool."""

from langchain_core.tools import tool

from Integrations.hotel_client import hotel_client


@tool
async def search_hotels(
    destination: str,
    check_in_date: str,
    check_out_date: str,
    adults: int = 1,
) -> list[dict]:
    """
    Search hotels for a destination.

    Args:
        destination: Destination city or location.
        check_in_date: Check-in date (YYYY-MM-DD).
        check_out_date: Check-out date (YYYY-MM-DD).
        adults: Number of adults.

    Returns:
        List of hotel options.
    """

    hotels = await hotel_client.search_hotels(
        destination=destination,
        check_in_date=check_in_date,
        check_out_date=check_out_date,
        adults=adults,
    )

    return [
        hotel.model_dump()
        for hotel in hotels
    ]