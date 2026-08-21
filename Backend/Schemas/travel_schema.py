"""Travel plan and travel package models."""

from typing import Literal
from pydantic import BaseModel, Field
from .activity_schema import PlaceSummary as ActivityOption
from .flight_schema import FlightOption
from .hotel_schema import HotelOption
from .currency_schema import PricingItem

class TravelPackage(BaseModel):
    """Complete travel package combining selected travel components."""

    why_this_package: str = Field(
        description="Reason why this package is recommended."
    )

    name: str = Field(
        description="Human-readable package name."
    )

    grade: Literal["Budget", "Balanced", "Premium"] = Field(
        description="Package tier."
    )

    selected_flight: FlightOption = Field(
        description="Selected flight option."
    )

    selected_hotel: HotelOption = Field(
        description="Selected hotel option."
    )

    selected_activities: list[ActivityOption] = Field(
        default_factory=list,
        max_length=2,
        description="Zero to two selected activities."
    )

    budget_comment: str = Field(
        description="How the package compares with the user's budget."
    )

    pricing_items: list[PricingItem] = Field(
        default_factory=list,
        description="Individual package pricing components."
    )


    converted_total_cost: float | None = Field(
        default=None,
        ge=0,
        description="Calculated package cost in the requested display currency."
    )

    converted_total_cost_currency: str | None = Field(
        default=None,
        description="Currency of the converted package cost."
    )

class TravelPlan(BaseModel):
    """Structured travel request extracted from the conversation."""

    # =========================
    # Origin
    # =========================
    origin: str | None = Field(default=None, description="Origin city or airport name.")
    destination: str | None = Field(default=None, description="Destination city or airport name.")
    departure_date: str | None = Field(default=None, description="Departure or check-in date in YYYY-MM-DD format.")
    return_date: str | None = Field(default=None, description="Return or check-out date in YYYY-MM-DD format.")
    duration_days: int | None = Field(default=None, ge=1, description="Trip duration in days.")
    adults: int = Field(default=1, ge=1, description="Number of adult travelers.")
    departure_time_pref: str | None = Field(default=None, description="Preferred departure time or time window.")
    arrival_time_pref: str | None = Field(default=None, description="Preferred arrival time or time window.")
    total_budget: float | None = Field(default=None, ge=0, description="Total trip budget.")
   
class TravelPackagesResponse(BaseModel):
    """Exactly three recommended travel packages."""

    travel_packages: list[TravelPackage] = Field(min_length=3, max_length=3, description="Exactly three packages: Budget, Balanced, and Premium.")