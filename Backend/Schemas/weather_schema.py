from typing import Annotated

from pydantic import BaseModel, Field


class WeatherResponse(BaseModel):
    """Current weather information useful for itinerary planning."""

    location: Annotated[str, Field(description="Destination city.")]
    temperature: Annotated[float | None, Field(default=None, description="Current temperature using the configured weather units.")]
    weather: Annotated[str | None, Field(default=None, description="Primary weather condition such as Clear, Rain, Snow or Clouds.")]
    description: Annotated[str, Field(description="Detailed weather description.")]
    humidity: Annotated[int | None, Field(default=None, description="Relative humidity percentage.")]
    visibility: Annotated[int | None, Field(default=None, description="Visibility in meters.")]

    model_config = {"frozen": True}