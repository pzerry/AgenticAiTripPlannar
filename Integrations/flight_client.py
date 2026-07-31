"""Flight client for SerpAPI Google Flights."""

from __future__ import annotations
from pydantic import ValidationError
import os

import httpx
from dotenv import load_dotenv

from Config import config
from Exceptions import FlightAPIError, ConfigurationError
from Logger.logger import get_logger
from Schemas.flight_schema import FlightOption, FlightDeal

load_dotenv()
logger = get_logger(__name__)

class FlightClient:
    """Client for searching flights using SerpAPI."""

    def __init__(self) -> None:
        self.base_url = config["flight"]["base_url"]
        self.timeout = config["flight"]["timeout"]

        self.api_key = os.getenv("SERP_API_KEY")

        if not self.api_key:
            raise ConfigurationError(
                "SERPAPI_API_KEY not found in environment variables."
            )

    async def search_flights(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        return_date: str | None = None,
        adults: int = 1,
        currency: str = "USD",
        travel_class:int=1,
        trip_type: int = 2,
    ) -> list[FlightOption]:
        """
        Search Google Flights via SerpAPI.
        """

        params = self._build_params(
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            return_date=return_date,
            adults=adults,
            currency=currency,
            travel_class=travel_class,
            trip_type=trip_type
        )

        data = await self._make_request(params)

        return self._parse_flights(data)

    def _build_params(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        return_date: str | None,
        adults: int,
        currency: str,
        travel_class: int,
        trip_type: int,
    ) -> dict:
        params = {
            "engine": "google_flights",
            "departure_id": origin,
            "arrival_id": destination,
            "outbound_date": departure_date,
            "currency": currency,
            "travel_class": travel_class,
            "adults": adults,
            "type": trip_type,
            "api_key": self.api_key,
        }

        if trip_type == 1 and return_date:
            params["return_date"] = return_date

        return params

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
        trip_type: int = 1,
        gl: str = "us",
        hl: str = "en",
    ) -> list[FlightDeal]:

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
            trip_type=trip_type,
            gl=gl,
            hl=hl,
        )

        data = await self._make_request(params)

        return self._parse_flight_deals(data)

    async def _make_request(self, params: dict) -> dict:

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout
            ) as client:

                response = await client.get(
                    self.base_url,
                    params=params,
                )

                response.raise_for_status()

                logger.info("Flights retrieved successfully.")

                return response.json()

        except httpx.TimeoutException as e:
            logger.exception(e)
        
        except httpx.HTTPStatusError as e:
            logger.exception("Flight request timed out.")
            raise FlightAPIError("Flight request timed out.") from e
                    
        
        except httpx.RequestError as e:
            logger.exception("Unable to reach Flight API.")
            raise FlightAPIError("Unable to reach Flight API.") from e

    def _parse_flights(
        self,
        data: dict,
    ) -> list[FlightOption]:
        """
        Convert SerpAPI response into FlightOption objects.
        """

        results: list[FlightOption] = []

        currency = data["search_parameters"].get("currency", "USD")

        for itinerary in data.get("best_flights", []):

            first_leg = itinerary["flights"][0]
            last_leg = itinerary["flights"][-1]

            results.append(
                FlightOption(
                    airline=first_leg["airline"],
                    flight_number=first_leg["flight_number"],
                    departure_airport=first_leg["departure_airport"]["id"],
                    arrival_airport=last_leg["arrival_airport"]["id"],
                    departure_time=first_leg["departure_airport"]["time"],
                    arrival_time=last_leg["arrival_airport"]["time"],
                    duration=f'{itinerary["total_duration"]} min',
                    stops=len(itinerary.get("layovers", [])),
                    price=f'{itinerary["price"]} {currency}',
                )
            )

        return results

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
        trip_type: int,
        gl: str,
        hl: str,
    ) -> dict:
        params = {
            "engine": "google_flights_deals",
            "departure_id": departure_id,
            "currency": currency,
            "travel_class": travel_class,
            "type": trip_type,
            "gl": gl,
            "hl": hl,
            "api_key": self.api_key,
        }

        if outbound_date:
            params["outbound_date"] = outbound_date

        if return_date:
            params["return_date"] = return_date

        if travel_duration:
            params["travel_duration"] = travel_duration

        if trip_length:
            params["trip_length"] = trip_length

        if max_price:
            params["max_price"] = max_price

        if stops is not None:
            params["stops"] = stops

        if include_airlines:
            params["include_airlines"] = include_airlines

        if exclude_airlines:
            params["exclude_airlines"] = exclude_airlines

        return params

    def _parse_flight_deals(
        self,
        data: dict,
    ) -> list[FlightDeal]:
        """Parse Google Flights Deals response."""

        currency = data.get("search_parameters", {}).get("currency", "USD")
        deals: list[FlightDeal] = []

        for item in data.get("deals", []):
            try:
                deals.append(
                    FlightDeal(
                        destination=item["name"],
                    destination_id=item["destination_id"],
                    country=item["country"],

                    price=item["price"],
                    average_price=item.get("average_price"),
                    currency=currency,
                    discount_percentage=item.get("discount_percentage"),

                    airline=item.get("airline"),
                    airline_code=item.get("airline_code"),

                    departure_airport=item["departure_airport_code"],
                    arrival_airport=item["arrival_airport_code"],

                    departure_date=item["outbound_date"],
                    return_date=item.get("return_date"),

                    duration_minutes=item["flight_duration"],
                    stops=item["stops"],

                    description=item.get("description"),
                    highlights=item.get("highlights"),

                    thumbnail=item.get("thumbnail"),

                    booking_url=item["flight_link"],
                    search_url=item["serpapi_flight_link"],
                

                    )
                )
            
            except ValidationError as e:
                logger.warning(
                    "Skipping malformed flight deal: %s\nData: %s",
                    e,
                    item,
                )

        return deals


flight_client = FlightClient()