"""TripAdvisor activity client."""

import os

import httpx
from dotenv import load_dotenv

from Config import config
from Exceptions import (
    ActivityAPIError,
    ConfigurationError,
)
from Logger.logger import get_logger
from Schemas.activity_schema import PlaceSummary

load_dotenv()

logger = get_logger(__name__)


class ActivityClient:
    """Client for TripAdvisor Search API."""

    def __init__(self):
        self.base_url = config["activity"]["base_url"]
        self.timeout = config["activity"]["timeout"]

        self.api_key = os.getenv("SERP_API_KEY")

        if not self.api_key:
            raise ConfigurationError(
                "SERP_API_KEY environment variable is not set."
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

    async def _make_request(
        self,
        params: dict,
    ) -> dict:
        """Send request to SerpAPI."""

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
            ) as client:
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

        return [
            PlaceSummary(
                place_id=item.get("place_id", ""),
                name=item.get("title", ""),
                category=item.get("place_type"),
                rating=item.get("rating"),
                reviews=item.get("reviews"),
                address=item.get("location"),
                description=item.get("description"),
                thumbnail=item.get("thumbnail"),
            )
            for item in data.get("places", [])
        ]


activity_client = ActivityClient()