from langchain_core.tools import tool

from integrations.weather_client import weather_client


@tool
async def get_current_weather(city: str) -> dict:
    """
    Retrieve the current weather conditions for a destination city.

    This tool returns weather information useful for itinerary planning,
    including temperature, perceived temperature, weather conditions,
    visibility, humidity, and sunrise/sunset times.

    Args:
        city: Destination city name.

    Returns:
        A dictionary containing the current weather details.
    """

    weather_response = await weather_client.get_current_weather(city)

    return weather_response.model_dump()