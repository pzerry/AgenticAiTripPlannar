"""Flight option model."""

from typing import Optional, Annotated
from pydantic import BaseModel, Field

class FlightOption(BaseModel):
    """Structured flight offer data."""

    airline: Annotated[str, Field(description="Operating airline name.")]
    flight_number: Annotated[str, Field(description="Flight number assigned by the airline.")]
    departure_airport: Annotated[str, Field(description="IATA code of the departure airport.")]
    arrival_airport: Annotated[str, Field(description="IATA code of the arrival airport.")]
    departure_time: Annotated[str, Field(description="Scheduled departure date and time.")]
    arrival_time: Annotated[str, Field(description="Scheduled arrival date and time.")]
    duration: Annotated[str, Field(description="Total travel duration.")]
    stops: Annotated[int, Field(description="Number of layovers.")]
    price: Annotated[str, Field(description="Total ticket price.")]