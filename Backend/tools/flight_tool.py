"""LangChain flight tools."""

from langchain_core.tools import tool

from Backend.Exceptions.exception import FlightAPIError
from Backend.integrations.flight_client import flight_client
from Backend.Logger.decorators import log_tool
from Backend.Logger.logger import get_logger


logger = get_logger(__name__)


@tool
@log_tool("search_flights")
async def search_flights(
    origin: str,
    destination: str,
    departure_date: str,
    return_date: str | None = None,
    adults: int = 1,
    currency: str = "USD",
    travel_class: int = 1,
) -> list[dict]:
    """
    Search flights between two airports.

    Args:
        origin: Origin airport IATA code.
        destination: Destination airport IATA code.
        departure_date: Departure date in YYYY-MM-DD format.
        return_date: Optional return date in YYYY-MM-DD format.
        adults: Number of adult travelers.
        currency: Currency code.
        travel_class:
            1 = Economy
            2 = Premium Economy
            3 = Business
            4 = First.

    Returns:
        Flight options as JSON-compatible dictionaries.
    """

    try:
        flights = await flight_client.search_flights(
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            return_date=return_date,
            adults=adults,
            currency=currency,
            travel_class=travel_class,
        )

        return [
            flight.model_dump(mode="json")
            for flight in flights
        ]

    except FlightAPIError:
        logger.exception(
            "Flight search failed."
        )
        raise



@tool
@log_tool("resolve_airports")
async def resolve_airports(
    origin: str,
    destination: str,
) -> dict:
    """
    Resolve origin and destination city names
    into airport IATA codes.
    """

    origin_airport, destination_airport = (
        await flight_client.resolve_airports(
            origin=origin,
            destination=destination,
        )
    )

    return {
        "origin_airport": origin_airport,
        "destination_airport": destination_airport,
    }

@tool
@log_tool("discover_flight_deals")
async def discover_flight_deals(
    departure_id: str,
    outbound_date: str | None = None,
    return_date: str | None = None,
    travel_duration: int | None = None,
    trip_length: str | None = None,
    max_price: int | None = None,
    travel_class: int = 1,
    stops: int | None = None,
    currency: str = "USD",
    include_airlines: str | None = None,
    exclude_airlines: str | None = None,
) -> list[dict]:
    """
    Discover discounted flight deals.
    """

    try:
        deals = await flight_client.search_flight_deals(
            departure_id=departure_id,
            outbound_date=outbound_date,
            return_date=return_date,
            travel_duration=travel_duration,
            trip_length=trip_length,
            max_price=max_price,
            travel_class=travel_class,
            stops=stops,
            currency=currency,
            include_airlines=include_airlines,
            exclude_airlines=exclude_airlines,
        )

        return [
            deal.model_dump(mode="json")
            for deal in deals
        ]

    except FlightAPIError:
        logger.exception(
            "Flight deals search failed."
        )
        raise