"""Client for SerpAPI Google Hotels."""

from __future__ import annotations

from datetime import date

import httpx
from pydantic import ValidationError

from Backend.Config import config
from Backend.Config.env import env
from Backend.Exceptions import ConfigurationError, HotelAPIError
from Backend.Logger.decorators import log_api
from Backend.Logger.logger import get_logger
from Backend.Schemas.hotel_schema import HotelOption


logger = get_logger(__name__)


class HotelClient:
    """Client for SerpAPI Google Hotels."""

    def __init__(self) -> None:
        self.base_url = config["hotel"]["base_url"]
        self.timeout = config["hotel"]["timeout"]
        self.api_key = env.SERPAPI_KEY

        if not self.api_key:
            raise ConfigurationError("SERPAPI_KEY not found in environment variables.")

    async def search_hotels(self, destination: str, check_in_date: str, check_out_date: str, adults: int = 1) -> list[HotelOption]:
        """Search hotels for a destination."""
        params = self._build_params(destination, check_in_date, check_out_date, adults)
        data = await self._make_request(params)
        return self._parse_hotels(data)

    def _build_params(self, destination: str, check_in_date: str, check_out_date: str, adults: int) -> dict:
        """Build and validate SerpAPI Google Hotels parameters."""
        if not destination or not destination.strip():
            raise HotelAPIError("Destination is required for hotel searches.")

        if adults < 1:
            raise HotelAPIError("Adults must be at least 1.")

        check_in = self._validate_date_format(check_in_date, "check_in_date")
        check_out = self._validate_date_format(check_out_date, "check_out_date")

        if check_in >= check_out:
            raise HotelAPIError("check_out_date must be after check_in_date.")

        return {
            "engine": "google_hotels",
            "q": destination.strip(),
            "check_in_date": check_in_date,
            "check_out_date": check_out_date,
            "adults": adults,
            "api_key": self.api_key,
            "children": config["hotel"].get("children", 0),
            "currency": config["travel"].get("currency", "USD"),
            "gl": config["hotel"].get("gl", "us"),
            "hl": config["hotel"].get("hl", "en"),
        }

    def _validate_date_format(self, date_str: str, field_name: str) -> date:
        """Validate YYYY-MM-DD date format."""
        try:
            return date.fromisoformat(date_str)
        except (TypeError, ValueError) as exc:
            raise HotelAPIError(f"{field_name} must be in YYYY-MM-DD format.") from exc

    @log_api("GoogleHotels")
    async def _make_request(self, params: dict) -> dict:
        """Execute the Google Hotels API request."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(self.base_url, params=params)
                response.raise_for_status()
                logger.info("Hotels retrieved successfully.")
                return response.json()

        except httpx.TimeoutException as exc:
            logger.exception("Hotel API request timed out.")
            raise HotelAPIError("Hotel API request timed out.") from exc

        except httpx.HTTPStatusError as exc:
            logger.exception("Hotel API returned %s\n%s", exc.response.status_code, exc.response.text)
            raise HotelAPIError(f"Hotel API Error ({exc.response.status_code}): {exc.response.text}") from exc

        except httpx.RequestError as exc:
            logger.exception("Unable to reach Hotel API.")
            raise HotelAPIError("Unable to reach Hotel API.") from exc

    def _parse_hotels(self, data: dict) -> list[HotelOption]:
        """Convert SerpAPI response into HotelOption objects."""
        hotels: list[HotelOption] = []
        properties = data.get("properties", [])[:3]

        currency = data.get("search_parameters", {}).get("currency") or config["travel"].get("currency", "USD")

        for property_data in properties:
            name = property_data.get("name")

            if not name:
                logger.warning("Skipping hotel without a name.")
                continue

            try:
                rate = property_data.get("rate_per_night") or {}
                total_rate = property_data.get("total_rate") or {}

                price_per_night = (
                    float(rate.get("extracted_lowest"))
                    if isinstance(rate, dict) and rate.get("extracted_lowest") is not None
                    else None
                )

                total_price = (
                    float(total_rate.get("extracted_lowest"))
                    if isinstance(total_rate, dict) and total_rate.get("extracted_lowest") is not None
                    else None
                )

                rating = property_data.get("overall_rating")
                rating = float(rating) if rating is not None else None

                reviews = property_data.get("reviews")
                reviews = int(reviews) if reviews is not None else None

                hotel_class = property_data.get("hotel_class")

                hotels.append(
                    HotelOption(
                        name=name,
                        price_per_night=price_per_night,
                        total_price=total_price,
                        currency=currency,
                        rating=rating,
                        reviews=reviews,
                        hotel_class=str(hotel_class) if hotel_class is not None else None,
                        address=property_data.get("address"),
                        amenities=property_data.get("amenities"),
                        check_in_time=property_data.get("check_in_time"),
                        check_out_time=property_data.get("check_out_time"),

                        free_cancellation=property_data.get("free_cancellation"),
                    )
                )

            except ValidationError as exc:
                logger.exception("Skipping invalid hotel: %s", exc)
                continue

            except (TypeError, ValueError) as exc:
                logger.exception("Failed to parse hotel price/rating fields: %s", exc)
                continue

        return hotels


hotel_client = HotelClient()