"""Flight client for SerpAPI Google Flights."""

from __future__ import annotations

import os

import httpx
from dotenv import load_dotenv

from Config import config
from Exceptions import FlightAPIError, ConfigurationError
from Logger import logger
from Schemas.flight_schema import FlightOption

load_dotenv()


class FlightClient:
    """Client for searching flights using SerpAPI."""

    def __init__(self) -> None:
        self.base_url = config["flight"]["base_url"]
        self.timeout = config["flight"]["timeout"]

        self.api_key = os.getenv("SERPAPI_API_KEY")

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
        travel_class: int = 1,
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
    ) -> dict:

        params = {
            "engine": "google_flights",
            "departure_id": origin,
            "arrival_id": destination,
            "outbound_date": departure_date,
            "currency": currency,
            "adults": adults,
            "travel_class": travel_class,
            "api_key": self.api_key,
        }

        if return_date:
            params["return_date"] = return_date

        return params

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
            logger.exception("Flight request timed out.")
            raise FlightAPIError("Flight request timed out.") from e

        except httpx.HTTPStatusError as e:
            logger.exception("Flight API returned HTTP error.")
            raise FlightAPIError(
                f"Flight API Error: {e.response.status_code}"
            ) from e

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

flight_client = FlightClient()