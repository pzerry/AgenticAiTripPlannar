"""Flight client for SerpAPI Google Flights."""

from __future__ import annotations

from datetime import date

import httpx

from Backend.Config import config
from Backend.Config.env import env
from Backend.Exceptions import ConfigurationError, FlightAPIError
from Backend.Logger.decorators import log_api
from Backend.Logger.logger import get_logger
from Backend.Schemas.flight_schema import FlightDeal, FlightOption


logger = get_logger(__name__)


class FlightClient:
    """Client for searching flights using SerpAPI."""

    def __init__(self) -> None:
        self.base_url = config["flight"]["base_url"]
        self.timeout = config["flight"]["timeout"]
        self.api_key = env.SERPAPI_KEY

        if not self.api_key:
            raise ConfigurationError("SERPAPI_KEY not found in environment variables.")

    # ==========================================================
    # Airport / Location Resolution
    # ==========================================================

    @log_api("SerpAPI-AirportResolver")
    async def resolve_airports(self, origin: str, destination: str) -> tuple[str, str]:
        """Resolve city/location names to airport IATA codes."""
        if not origin or not origin.strip():
            raise FlightAPIError("Origin is required for airport resolution.")

        if not destination or not destination.strip():
            raise FlightAPIError("Destination is required for airport resolution.")

        origin_airport = await self._resolve_city_airport(origin)
        destination_airport = await self._resolve_city_airport(destination)

        logger.info("Resolved flight route: %s -> %s", origin_airport, destination_airport)
        return origin_airport, destination_airport

    async def _resolve_city_airport(self, city: str) -> str:
        """Resolve one city/location to an airport IATA code."""
        params = {"engine": "google_flights_autocomplete", "q": city.strip(), "hl": "en", "api_key": self.api_key}
        data = await self._make_request(params)
        suggestions = data.get("suggestions", [])

        if not suggestions:
            raise FlightAPIError(f"No airport suggestions found for: {city}")

        city_normalized = city.strip().lower()

        for suggestion in suggestions:
            suggestion_type = suggestion.get("type")
            suggestion_name = str(suggestion.get("name", "")).strip().lower()

            if suggestion_type == "city" and suggestion_name == city_normalized:
                airport_code = self._first_airport_code(suggestion)
                if airport_code:
                    return airport_code

        for suggestion in suggestions:
            if suggestion.get("type") != "city":
                continue

            airport_code = self._first_airport_code(suggestion)
            if airport_code:
                return airport_code

        for suggestion in suggestions:
            airport_code = self._first_airport_code(suggestion)
            if airport_code:
                return airport_code

        raise FlightAPIError(f"Could not resolve airport for: {city}")

    @staticmethod
    def _first_airport_code(suggestion: dict) -> str | None:
        """Extract the first airport IATA code from a suggestion."""
        airports = suggestion.get("airports", [])

        if not isinstance(airports, list):
            return None

        for airport in airports:
            if not isinstance(airport, dict):
                continue

            airport_id = airport.get("id")

            if isinstance(airport_id, str) and len(airport_id) == 3 and airport_id.isalpha() and airport_id.isupper():
                return airport_id

        return None

    # ==========================================================
    # Flight Search
    # ==========================================================

    @log_api("SerpAPI")
    async def search_flights(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        return_date: str | None = None,
        adults: int = 1,
        currency: str = "USD",
        travel_class: int = 1,
    ) -> list[FlightOption]:
        """Search Google Flights using airport IATA codes."""
        params = self._build_params(origin, destination, departure_date, return_date, adults, currency, travel_class)
        data = await self._make_request(params)
        flights = self._parse_flights(data)

        logger.info("Retrieved %d flight itineraries.", len(flights))
        return flights

    def _build_params(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        return_date: str | None,
        adults: int,
        currency: str,
        travel_class: int,
    ) -> dict:
        """Build Google Flights request parameters."""
        if not origin:
            raise FlightAPIError("Origin airport is required.")

        if not destination:
            raise FlightAPIError("Destination airport is required.")

        params = {
            "engine": "google_flights",
            "departure_id": origin,
            "arrival_id": destination,
            "outbound_date": departure_date,
            "currency": currency,
            "travel_class": travel_class,
            "adults": adults,
            "api_key": self.api_key,
            "hl": "en",
            "type": 1 if return_date else 2,
        }

        if return_date:
            params["return_date"] = return_date

        return params

    # ==========================================================
    # HTTP Request
    # ==========================================================

    async def _make_request(self, params: dict) -> dict:
        """Execute HTTP request against SerpAPI."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(self.base_url, params=params)
                response.raise_for_status()
                return response.json()

        except httpx.TimeoutException as exc:
            logger.exception("Flight API request timed out.")
            raise FlightAPIError("Flight API request timed out.") from exc

        except httpx.HTTPStatusError as exc:
            logger.exception("Flight API returned %s\n%s", exc.response.status_code, exc.response.text)
            raise FlightAPIError(f"Flight API Error ({exc.response.status_code}): {exc.response.text}") from exc

        except httpx.RequestError as exc:
            logger.exception("Unable to reach Flight API.")
            raise FlightAPIError("Unable to reach Flight API.") from exc

    # ==========================================================
    # Flight Response Parsing
    # ==========================================================

    def _parse_flights(self, data: dict) -> list[FlightOption]:
        """Convert SerpAPI flight response into FlightOption objects."""
        results: list[FlightOption] = []

        currency = data.get("search_parameters", {}).get("currency", "USD")

        for itinerary in data.get("best_flights", []):
            flights = itinerary.get("flights", [])

            if not flights:
                continue

            first_leg = flights[0]
            last_leg = flights[-1]
            departure_airport = first_leg.get("departure_airport", {})
            arrival_airport = last_leg.get("arrival_airport", {})

            try:
                results.append(
                    FlightOption(
                        airline=first_leg.get("airline", "Unknown"),
                        flight_number=str(first_leg.get("flight_number", "")),
                        departure_airport=departure_airport.get("id", ""),
                        arrival_airport=arrival_airport.get("id", ""),
                        departure_time=departure_airport.get("time", ""),
                        arrival_time=arrival_airport.get("time", ""),
                        duration=itinerary.get("total_duration", 0),
                        stops=len(itinerary.get("layovers", [])),
                        price=float(itinerary.get("price", 0)),
                        currency=currency,
                    )
                )
            except Exception:
                logger.exception("Failed to parse a flight itinerary.")
                continue

        return results

    # ==========================================================
    # Flight Deals
    # ==========================================================

    async def search_flight_deals(
        self,
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
        gl: str = "us",
        hl: str = "en",
    ) -> list[FlightDeal]:
        """Search discounted flight deals."""
        params = self._build_deals_params(
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
            gl=gl,
            hl=hl,
        )

        data = await self._make_request(params)
        deals = self._parse_flight_deals(data)

        logger.info("Retrieved %d flight deals.", len(deals))
        return deals

    def _build_deals_params(
        self,
        departure_id: str,
        outbound_date: str | None,
        return_date: str | None,
        travel_duration: int | None,
        trip_length: str | None,
        max_price: int | None,
        travel_class: int,
        stops: int | None,
        currency: str,
        include_airlines: str | None,
        exclude_airlines: str | None,
        gl: str,
        hl: str,
    ) -> dict:
        """Build Google Flights deals request parameters."""
        params = {
            "engine": "google_flights_deals",
            "departure_id": departure_id,
            "currency": currency,
            "travel_class": travel_class,
            "gl": gl,
            "hl": hl,
            "api_key": self.api_key,
            "type": 1 if return_date else 2,
        }

        if outbound_date:
            params["outbound_date"] = outbound_date

        if return_date:
            params["return_date"] = return_date

        if travel_duration is not None:
            params["travel_duration"] = travel_duration

        if trip_length:
            params["trip_length"] = trip_length

        if max_price is not None:
            params["max_price"] = max_price

        if stops is not None:
            params["stops"] = stops

        if include_airlines:
            params["include_airlines"] = include_airlines

        if exclude_airlines:
            params["exclude_airlines"] = exclude_airlines

        return params

    def _parse_flight_deals(self, data: dict) -> list[FlightDeal]:
        """Convert SerpAPI flight deals into FlightDeal models."""
        results: list[FlightDeal] = []
        currency = data.get("search_parameters", {}).get("currency", "USD")

        for deal in data.get("deals", []):
            try:
                departure_date = date.fromisoformat(deal["start_date"]) if deal.get("start_date") else date.today()
                return_date = date.fromisoformat(deal["end_date"]) if deal.get("end_date") else None

                results.append(
                    FlightDeal(
                        destination=deal.get("name", ""),
                        destination_id=deal.get("destination_id", ""),
                        country=deal.get("country", ""),
                        price=float(deal.get("price", 0)),
                        average_price=deal.get("average_price"),
                        currency=currency,
                        discount_percentage=deal.get("discount_percentage"),
                        airline=deal.get("airline"),
                        airline_code=deal.get("airline_code"),
                        departure_airport=deal.get("departure_airport_code", ""),
                        arrival_airport=deal.get("arrival_airport_code", ""),
                        departure_date=departure_date,
                        return_date=return_date,
                        duration_minutes=deal.get("flight_duration", 0),
                        stops=deal.get("stops", 0),
                        description=deal.get("description"),
                        highlights=deal.get("highlights"),
                        thumbnail=deal.get("thumbnail"),
                        booking_url=deal.get("flight_link", ""),
                        search_url=deal.get("serpapi_flight_link", ""),
                    )
                )
            except Exception:
                logger.exception("Failed to parse flight deal.")
                continue

        return results


flight_client = FlightClient()