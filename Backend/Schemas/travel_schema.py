"""Travel plan models."""

from pydantic import BaseModel, Field


class TravelPlan(BaseModel):
    origin: str | None = Field(default=None, description="Origin city or airport name.")
    destination: str | None = Field(default=None, description="Destination city or airport name.")
    departure_date: str | None = Field(default=None, description="Departure or check-in date in YYYY-MM-DD format.")
    return_date: str | None = Field(default=None, description="Return or check-out date in YYYY-MM-DD format.")
    duration_days: int | None = Field(default=None, ge=1, description="Trip duration in days.")
    adults: int = Field(default=1, ge=1, description="Number of adult travelers.")
    departure_time_pref: str | None = Field(default=None, description="Preferred departure time or time window.")
    arrival_time_pref: str | None = Field(default=None, description="Preferred arrival time or time window.")
    total_budget: float | None = Field(default=None, ge=0, description="Total trip budget.")
    preferred_flight_type: str | None = Field(default=None, description="Preferred flight type, such as non_stop or connecting.")
    preferred_hotel_class: str | None = Field(default=None, description="Preferred hotel class, such as 3_star, 4_star, or 5_star.")
    preferred_trip_style: str | None = Field(default=None, description="General trip style: budget_friendly, balanced, or luxury.")
