"""LangChain weather tool."""

from langchain_core.tools import tool

from Backend.Exceptions.exception import ConfigurationError, WeatherAPIError
from Backend.Logger.decorators import log_tool
from Backend.Logger.logger import get_logger
from Backend.integrations.weather_client import WeatherClient


logger = get_logger(__name__)
weather_client = WeatherClient()


@tool
@log_tool("get_current_weather")
async def get_current_weather(city: str) -> dict:
    """Retrieve current weather conditions for a destination city."""
    try:
        weather_response = await weather_client.get_current_weather(city)
        return weather_response.model_dump(mode="json")

    except (ConfigurationError, WeatherAPIError):
        logger.exception("Weather unavailable for %s.", city)

        return {
            "location": city,
            "temperature": None,
            "weather": None,
            "description": "Weather information unavailable.",
            "humidity": None,
            "visibility": None,
        }