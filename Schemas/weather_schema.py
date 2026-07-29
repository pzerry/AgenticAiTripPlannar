from pydantic import BaseModel, Field


class WeatherResponse(BaseModel):
    """Weather information returned by the application."""

    city: str = Field(..., description="City name")
    country: str = Field(..., description="Country code")

    temperature: float = Field(..., description="Current temperature in Celsius")
    humidity: int = Field(..., description="Humidity percentage")
    weather: str = Field(..., description="Weather condition")
    description: str = Field(..., description="Detailed weather description")

    wind_speed: float = Field(..., description="Wind speed in m/s")

    class Config:
        frozen = True
