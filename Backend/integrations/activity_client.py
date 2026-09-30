"""TripAdvisor activity client."""

from __future__ import annotations

import httpx
from math import isfinite
from pydantic import ValidationError

from Backend.Config import config
from Backend.Config.env import env
from Backend.Exceptions import ActivityAPIError, ConfigurationError
from Backend.Logger import get_logger
from Backend.Logger.decorators import log_api
from Backend.Schemas.activity_schema import PlaceSummary


logger = get_logger(__name__)


class ActivityClient:
    """Client for TripAdvisor Search API via SerpAPI."""

    def __init__(self) -> None:
        self.base_url = config["activity"]["base_url"]
        self.timeout = config["activity"]["timeout"]
        self.api_key = env.SERPAPI_KEY

        if not self.api_key:
            raise ConfigurationError("SERP_API_KEY environment variable is not set.")

    async def search_places(self, query: str, location: str | None = None) -> list[PlaceSummary]:
        """Search TripAdvisor and return up to ten ranked activity candidates."""
        if not query or not query.strip():
            raise ActivityAPIError("Search query is required.")

        params = self._build_search_params(query, location)
        data = await self._make_request(params)
        places = self._parse_search(data)

        # Rank all valid results before truncating, so a highly rated place
        # near the end of SerpAPI's response can still reach the selection LLM.
        # Missing/non-finite ratings rank last; review count breaks rating ties.
        # Equal scores keep the provider's original order (Python's stable sort).
        ranked = sorted(
            places,
            key=lambda place: (
                place.rating if place.rating is not None and isfinite(place.rating) else -1,
                place.reviews if place.reviews is not None else 0,
            ),
            reverse=True,
        )
        candidates = ranked[:10]
        logger.info("Shortlisted %d of %d activities for selection.", len(candidates), len(places))
        return candidates

    def _build_search_params(self, query: str, location: str | None = None) -> dict:
        """Build TripAdvisor search request parameters."""
        params = {"engine": "tripadvisor", "q": query.strip(), "api_key": self.api_key}

        if location and location.strip():
            params["location"] = location.strip()

        return params

    @log_api("TripAdvisor")
    async def _make_request(self, params: dict) -> dict:
        """Send request to SerpAPI."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(self.base_url, params=params)
                response.raise_for_status()
                logger.info("Activities retrieved successfully.")
                return response.json()

        except httpx.TimeoutException as exc:
            logger.exception("TripAdvisor request timed out.")
            raise ActivityAPIError("TripAdvisor service timed out.") from exc

        except httpx.HTTPStatusError as exc:
            logger.exception("TripAdvisor API request failed. status=%s", exc.response.status_code)
            raise ActivityAPIError(f"TripAdvisor API Error ({exc.response.status_code}): {exc.response.text}") from exc

        except httpx.RequestError as exc:
            logger.exception("Unable to connect to TripAdvisor.")
            raise ActivityAPIError("Unable to connect to TripAdvisor.") from exc

    def _parse_search(self, data: dict) -> list[PlaceSummary]:
        """Convert API response into PlaceSummary objects."""
        places: list[PlaceSummary] = []

        for item in data.get("places", []):
            name = item.get("title")

            if not name:
                logger.warning("Skipping place without a name.")
                continue

            try:
                rating = item.get("rating")
                rating = float(rating) if rating is not None else None

                reviews = item.get("reviews")
                reviews = int(reviews) if reviews is not None else None

                places.append(
                    PlaceSummary(
                        name=name,
                        category=item.get("place_type"),
                        rating=rating,
                        reviews=reviews,
                        address=item.get("location"),
                        description=item.get("description"),
                        
                    )
                )

            except (ValidationError, TypeError, ValueError) as exc:
                logger.exception("Skipping invalid place: %s", exc)
                continue

        logger.info("Parsed %d activities.", len(places))
        return places


activity_client = ActivityClient()
