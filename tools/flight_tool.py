"""LangChain flight tools."""

from langchain_core.tools import tool

from Integrations.flight_client import flight_client


@tool
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
    Search flights between two locations.

    Args:
        origin: IATA airport code (e.g. DEL).
        destination: IATA airport code (e.g. NRT).
        departure_date: Departure date (YYYY-MM-DD).
        return_date: Optional return date (YYYY-MM-DD).
        adults: Number of adults.
        currency: Currency code (USD, INR, EUR).
        travel_class:
            1 = Economy
            2 = Premium Economy
            3 = Business
            4 = First

    Returns:
        List of available flight options.
    """

    flights = await flight_client.search_flights(
        origin=origin,
        destination=destination,
        departure_date=departure_date,
        return_date=return_date,
        adults=adults,
        currency=currency,
        travel_class=travel_class,
    )

    return [flight.model_dump() for flight in flights]


@tool
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
    trip_type: int = 1,
) -> list[dict]:
    """
    Discover discounted flight deals from a departure airport or city.

    Args:
        departure_id:
            Airport code (DEL, LHR, CDG) or Google city ID (/m/04jpl).

        outbound_date:
            Departure date (YYYY-MM-DD) or date range
            (YYYY-MM-DD,YYYY-MM-DD).

        return_date:
            Return date or return date range.

        travel_duration:
            Number of travel days for flexible search.

        trip_length:
            Trip length range such as "5,10".

        max_price:
            Maximum budget.

        travel_class:
            1 = Economy
            2 = Premium Economy
            3 = Business
            4 = First

        stops:
            Maximum number of stops.

        currency:
            Currency code.

        include_airlines:
            Airline codes separated by commas.
            Example: "AI,6E"

        exclude_airlines:
            Airline codes separated by commas.

        trip_type:
            1 = Round Trip
            2 = One Way

    Returns:
        List of discounted flight deals.
    """

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
        trip_type=trip_type,
    )

    return [deal.model_dump() for deal in deals]