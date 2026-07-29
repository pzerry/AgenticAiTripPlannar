from langchain_core.tools import tool

from Integrations import flight_client


@tool
async def search_flights(
    origin: str,
    destination: str,
    departure_date: str,
) -> list[dict]: 
    """Search available flights."""

    flights = await flight_client.search_flights(
        origin=origin,
        destination=destination,
        departure_date=departure_date,
    )

    return [flight.model_dump() for flight in flights]