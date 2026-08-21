"""OpenWeather current weather client."""

from __future__ import annotations

import httpx

from Backend.Config import config
from Backend.Config.env import env
from Backend.Exceptions import ConfigurationError, WeatherAPIError
from Backend.Logger.decorators import log_api
from Backend.Logger.logger import get_logger
from Backend.Schemas.weather_schema import WeatherResponse


logger = get_logger(__name__)


class WeatherClient:
    """Client for interacting with the OpenWeather Current Weather API."""

    def __init__(self) -> None:
        self.base_url = config["weather"]["base_url"]
        self.timeout = config["weather"]["timeout"]
        self.units = config["weather"]["units"]
        self.api_key = env.OPENWEATHERMAP_API_KEY

        if not self.api_key:
            raise ConfigurationError("OPENWEATHERMAP_API_KEY is missing.")

    @log_api("OpenWeather")
    async def get_current_weather(self, city: str) -> WeatherResponse:
        """Fetch current weather for a city."""
        if not city or not city.strip():
            raise WeatherAPIError("Destination city is required.")

        params = {"q": city.strip(), "appid": self.api_key, "units": self.units}
        url = f"{self.base_url}/weather"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()

        except httpx.TimeoutException as exc:
            logger.exception("OpenWeather request timed out.")
            raise WeatherAPIError("Weather service timed out.") from exc

        except httpx.HTTPStatusError as exc:
            logger.exception("OpenWeather returned status %s.", exc.response.status_code)
            raise WeatherAPIError("Weather service returned an invalid response.") from exc

        except httpx.RequestError as exc:
            logger.exception("Unable to connect to OpenWeather.")
            raise WeatherAPIError("Unable to connect to weather service.") from exc

        try:
            data = response.json()
            weather_data = data["weather"][0]
            main_data = data["main"]

            return WeatherResponse(
                location=data["name"],
                temperature=float(main_data["temp"]),
                weather=weather_data["main"],
                description=weather_data["description"],
                humidity=int(main_data["humidity"]),
                visibility=int(data.get("visibility", 10000)),
            )

        except (KeyError, IndexError, TypeError, ValueError) as exc:
            logger.exception("Invalid weather response received from OpenWeather.")
            raise WeatherAPIError("Weather service returned an invalid response.") from exc