import os

import httpx
from dotenv import load_dotenv
from Logger import logger
from Config import config
from Exceptions import ConfigurationError, WeatherAPIError
from Schemas.weather_schema import WeatherResponse

load_dotenv()


class WeatherClient:
    """Client for interacting with the OpenWeather API."""

    def __init__(self):
        self.base_url = config["weather"]["base_url"]
        self.timeout = config["weather"]["timeout"]
        self.units = config["weather"]["units"]
        self.api_key = os.getenv("OPENWEATHERMAP_API_KEY")

        if not self.api_key:
            raise ConfigurationError(
                "OPENWEATHERMAP_API_KEY is missing."
            )

    async def get_current_weather(
        self,
        city: str,
    ) -> WeatherResponse:
        """Fetch current weather for a city."""

        url = f"{self.base_url}/weather"

        params = {
            "q": city,
            "appid": self.api_key,
            "units": self.units,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    url,
                    params=params,
                )

            response.raise_for_status()

        except httpx.TimeoutException as e:
            logger.exception("OpenWeather request timed out.")
            raise WeatherAPIError("Weather service timed out.") from e

        except httpx.HTTPStatusError as e:
            logger.exception("OpenWeather returned an error.")
            raise WeatherAPIError("Weather service returned an invalid response.") from e

        except httpx.RequestError as e:
            logger.exception("Unable to connect to OpenWeather.")
            raise WeatherAPIError("Unable to connect to weather service.") from e

        response.raise_for_status()

        data = response.json()

        return WeatherResponse(
            city=data["name"],
            country=data["sys"]["country"],
            temperature=data["main"]["temp"],
            feels_like=data["main"]["feels_like"],
            humidity=data["main"]["humidity"],
            pressure=data["main"]["pressure"],
            weather=data["weather"][0]["main"],
            description=data["weather"][0]["description"],
            wind_speed=data["wind"]["speed"],
        )


weather_client = WeatherClient()