from pydantic import BaseModel, Field


class WeatherResponse(BaseModel):
    """Weather information returned by the application."""

    location: Annotated[str, Field(description="City, region, or destination for which the weather information is provided.")]

from typing import Annotated

from pydantic import BaseModel, Field


class WeatherResponse(BaseModel):
    """Current weather information useful for itinerary planning."""

    location: Annotated[
        str,
        Field(description="Destination city.")
    ]

    temperature: Annotated[
        float,
        Field(description="Current temperature in Celsius.")
    ]

    feels_like: Annotated[
        float,
        Field(description="Perceived temperature in Celsius.")
    ]

    weather: Annotated[
        str,
        Field(description="Primary weather condition such as Clear, Rain, Snow or Clouds.")
    ]

    description: Annotated[
        str,
        Field(description="Detailed weather description.")
    ]

    humidity: Annotated[
        int,
        Field(description="Relative humidity percentage.")
    ]

    visibility: Annotated[
        int,
        Field(description="Visibility in meters.")
    ]

    sunrise: Annotated[
        int,
        Field(description="Sunrise Unix timestamp.")
    ]

    sunset: Annotated[
        int,
        Field(description="Sunset Unix timestamp.")
    ]

    model_config = {
        "frozen": True
    }