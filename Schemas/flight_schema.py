"""Flight option model."""
from datetime import date
from typing import Optional, Annotated
from pydantic import BaseModel, Field, PositiveFloat, PositiveInt, NonNegativeInt, HttpUrl

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


class FlightDeal(BaseModel):
    destination: Annotated[str, Field(description="Destination city or airport name.")]
    destination_id: Annotated[str, Field(description="Unique destination identifier or IATA airport code.")]
    country: Annotated[str, Field(description="Country of the destination.")]
    price: Annotated[PositiveFloat, Field(description="Current ticket price in the specified currency.")]
    average_price: Annotated[PositiveFloat | None, Field(default=None, description="Average historical ticket price for this route.")]
    currency: Annotated[str, Field(description="Three-letter ISO currency code (e.g., USD, INR, EUR).")]
    discount_percentage: Annotated[NonNegativeInt | None, Field(default=None, description="Percentage discount compared to the average ticket price.")]
    airline: Annotated[str | None, Field(default=None, description="Name of the operating airline.")]
    airline_code: Annotated[str | None, Field(default=None, description="IATA airline code (e.g., AI, 6E, UK).")]
    departure_airport: Annotated[str, Field(description="IATA code of the departure airport.")]
    arrival_airport: Annotated[str, Field(description="IATA code of the arrival airport.")]
    departure_date: Annotated[date, Field(description="Scheduled departure date.")]
    return_date: Annotated[date | None, Field(default=None, description="Scheduled return date for round-trip journeys.")]
    duration_minutes: Annotated[PositiveInt, Field(description="Total travel duration in minutes.")]
    stops: Annotated[NonNegativeInt, Field(description="Number of layovers during the journey.")]
    description: Annotated[str | None, Field(default=None, description="Brief description of the flight deal.")]
    highlights: Annotated[str | None, Field(default=None, description="Key highlights such as cheapest fare, shortest duration, or best value.")]
    thumbnail: Annotated[HttpUrl | None, Field(default=None, description="URL of an image representing the destination or airline.")]
    booking_url: Annotated[HttpUrl, Field(description="Direct URL to book the flight.")]
    search_url: Annotated[HttpUrl, Field(description="URL to the search results page containing this flight deal.")]

    
class FlightDealsResponse(BaseModel):
    departure_city: Annotated[str, Field(description="City from which all flight deals originate.")]
    departure_airport: Annotated[str | None, Field(default=None, description="IATA code of the departure airport used for the search.")]
    currency: Annotated[str, Field(description="Three-letter ISO currency code used for all flight prices (e.g., USD, INR, EUR).")]
    deals: Annotated[list[FlightDeal], Field(description="List of flight deals matching the search criteria.")]