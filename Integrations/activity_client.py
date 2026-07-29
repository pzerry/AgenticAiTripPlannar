"""TripAdvisor activity client."""

import os

import httpx
from dotenv import load_dotenv

from Config import config
from Exceptions import (
    ActivityAPIError,
    ConfigurationError,
)
from Logger import logger
from Schemas.activity_schema import (
    PlaceDetails,
    PlaceSummary,
    NearbyPlace,
    OperatingHours,
)

load_dotenv()


class ActivityClient:
    """Client for TripAdvisor Search API."""

    def __init__(self):
        self.base_url = config["activity"]["base_url"]
        self.timeout = config["activity"]["timeout"]

        self.api_key = os.getenv("SERPAPI_API_KEY")

        if not self.api_key:
            raise ConfigurationError(
                "SERPAPI_API_KEY environment variable is not set."
            )

    async def search_places(
        self,
        query: str,
        location: str | None = None,
    ) -> list[PlaceSummary]:
        """Search TripAdvisor places."""

        params = self._build_search_params(
            query=query,
            location=location,
        )

        data = await self._make_request(params)

        return self._parse_search(data)

    async def get_place_details(
        self,
        place_id: str,
    ) -> PlaceDetails:
        """Retrieve detailed information about a place."""

        params = self._build_detail_params(place_id)

        data = await self._make_request(params)

        return self._parse_details(data)

    def _build_search_params(
        self,
        query: str,
        location: str | None = None,
    ) -> dict:
        """Build search request parameters."""

        params = {
            "engine": "tripadvisor",
            "q": query,
            "api_key": self.api_key,
        }

        if location:
            params["location"] = location

        return params

    def _build_detail_params(
        self,
        place_id: str,
    ) -> dict:
        """Build place details request parameters."""

        return {
            "engine": "tripadvisor_place",
            "place_id": place_id,
            "api_key": self.api_key,
        }

    async def _make_request(
        self,
        params: dict,
    ) -> dict:
        """Send request to SerpAPI."""

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    self.base_url,
                    params=params,
                )

            response.raise_for_status()

            return response.json()

        except httpx.TimeoutException as e:
            logger.exception("TripAdvisor request timed out.")
            raise ActivityAPIError(
                "TripAdvisor service timed out."
            ) from e

        except httpx.HTTPStatusError as e:
            logger.exception("TripAdvisor returned an error.")
            raise ActivityAPIError(
                "TripAdvisor returned an invalid response."
            ) from e

        except httpx.RequestError as e:
            logger.exception("Unable to connect to TripAdvisor.")
            raise ActivityAPIError(
                "Unable to connect to TripAdvisor."
            ) from e

    def _parse_search(
        self,
        data: dict,
    ) -> list[PlaceSummary]:
        """Parse search response."""

        results = []

        for item in data.get("data", []):

            results.append(
                PlaceSummary(
                    place_id=item.get("place_id", ""),
                    name=item.get("name", ""),
                    category=item.get("type"),
                    rating=item.get("rating"),
                    reviews=item.get("reviews"),
                    address=item.get("address"),
                )
            )

        return results

    def _parse_details(
        self,
        data: dict,
    ) -> PlaceDetails:
        """Parse place details response."""

        place = data.get("place_result", {})

        opening_hours = [
            OperatingHours(
                day=hour.get("day", ""),
                hours=hour.get("hours", ""),
            )
            for hour in place.get("opening_hours", [])
        ]

        nearby_hotels = [
            NearbyPlace(
                place_id=item.get("place_id", ""),
                name=item.get("name", ""),
                rating=item.get("rating"),
                reviews=item.get("reviews"),
            )
            for item in place.get("nearby_hotels", [])
        ]

        nearby_restaurants = [
            NearbyPlace(
                place_id=item.get("place_id", ""),
                name=item.get("name", ""),
                rating=item.get("rating"),
                reviews=item.get("reviews"),
            )
            for item in place.get("nearby_restaurants", [])
        ]

        nearby_attractions = [
            NearbyPlace(
                place_id=item.get("place_id", ""),
                name=item.get("name", ""),
                rating=item.get("rating"),
                reviews=item.get("reviews"),
            )
            for item in place.get("nearby_attractions", [])
        ]

        return PlaceDetails(
            place_id=place.get("place_id", ""),
            name=place.get("name", ""),
            category=place.get("type"),
            rating=place.get("rating"),
            reviews=place.get("reviews"),
            address=place.get("address"),
            website=place.get("website"),
            phone=place.get("phone"),
            description=place.get("description"),
            opening_hours=opening_hours,
            images=place.get("images", []),
            nearby_hotels=nearby_hotels,
            nearby_restaurants=nearby_restaurants,
            nearby_attractions=nearby_attractions,
        )