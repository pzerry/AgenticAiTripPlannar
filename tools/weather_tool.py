from langchain_core.tools import tool
from Integrations.weather import weather_client

@tool
async def get_current_weather(city: str,) -> dict:
    """
    Get the current weather for a city.

    Args:
        city: Name of the city.
    """

    weather = await weather_client.get_current_weather(city)

    return weather.model_dump()