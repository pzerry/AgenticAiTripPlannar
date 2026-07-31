"""Client for SerpAPI Google Hotels."""

import os

import httpx
from dotenv import load_dotenv

from Config import config
from Exceptions import ConfigurationError, HotelAPIError
from Logger.logger import get_logger
from Schemas.hotel_schema import HotelOption

load_dotenv()
logger = get_logger(__name__)


class HotelClient:
    """Client for SerpAPI Google Hotels."""

    def __init__(self):
        self.base_url = config["hotel"]["base_url"]
        self.timeout = config["hotel"]["timeout"]

        self.api_key = os.getenv("SERP_API_KEY")

        if not self.api_key:
            raise ConfigurationError("SERP_API_KEY is not configured.")

    async def search_hotels(
        self,
        destination: str,
        check_in_date: str,
        check_out_date: str,
        adults: int = 1,
    ) -> list[HotelOption]:
        """
        Search hotels for a destination.
        """

        params = self._build_params(
            destination=destination,
            check_in_date=check_in_date,
            check_out_date=check_out_date,
            adults=adults,
        )

        data = await self._make_request(params)

        return self._parse_hotels(data)

    def _build_params(
        self,
        destination: str,
        check_in_date: str,
        check_out_date: str,
        adults: int,
    ) -> dict:
        """
        Build query parameters.
        """

        return {
            "engine": "google_hotels",
            "q": destination,
            "check_in_date": check_in_date,
            "check_out_date": check_out_date,
            "adults": adults,
            "api_key": self.api_key,
        }

    async def _make_request(
        self,
        params: dict,
    ) -> dict:
        """
        Execute HTTP request.
        """

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
            ) as client:

                response = await client.get(
                    self.base_url,
                    params=params,
                )

                response.raise_for_status()

                logger.info("Hotels retrieved successfully.")

                return response.json()

        except httpx.HTTPStatusError as e:
            logger.exception(e)

            raise HotelAPIError(
                f"Hotel API returned {e.response.status_code}"
            ) from e

        except httpx.RequestError as e:
            logger.exception(e)

            raise HotelAPIError(
                f"Hotel API request failed: {e}"
            ) from e

    def _parse_hotels(
        self,
        data: dict,
    ) -> list[HotelOption]:
        """
        Convert API response into HotelOption objects.
        """

        hotels: list[HotelOption] = []

        properties = data.get("properties", [])

        for property_data in properties:

            rate = property_data.get("rate_per_night", {})
            total_rate = property_data.get("total_rate", {})

            hotels.append(
                HotelOption(
                    name=property_data.get("name", "Unknown Hotel"),
                    price_per_night=(
                        rate.get("extracted_lowest")
                        if isinstance(rate, dict)
                        else None
                    ),
                    total_price=(
                        total_rate.get("extracted_lowest")
                        if isinstance(total_rate, dict)
                        else None
                    ),
                    rating=property_data.get("overall_rating"),
                    reviews=property_data.get("reviews"),
                    hotel_class=property_data.get("hotel_class"),
                    address=property_data.get("address"),
                    thumbnail=property_data.get("thumbnail"),
                    amenities=property_data.get("amenities", []),
                    check_in_time=property_data.get("check_in_time"),
                    check_out_time=property_data.get("check_out_time"),
                    booking_link=property_data.get("link"),
                    free_cancellation=property_data.get("free_cancellation"),
                    source="Google Hotels",
                )
            )

        return hotels


hotel_client = HotelClient()