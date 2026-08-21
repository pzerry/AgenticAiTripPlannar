"""LangChain hotel tools."""

from langchain_core.tools import tool

from Backend.Exceptions.exception import HotelAPIError
from Backend.integrations.hotel_client import hotel_client
from Backend.Logger.decorators import log_tool
from Backend.Logger.logger import get_logger


logger = get_logger(__name__)


@tool
@log_tool("search_hotels")
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
        adults: Number of adult travelers.

    Returns:
        List of hotel options as JSON-compatible dictionaries.
    """

    try:
        hotels = await hotel_client.search_hotels(
            destination=destination,
            check_in_date=check_in_date,
            check_out_date=check_out_date,
            adults=adults,
        )

        return [
            hotel.model_dump(mode="json")
            for hotel in hotels
        ]

    except HotelAPIError:
        logger.exception(
            "Hotel search failed."
        )
        raise