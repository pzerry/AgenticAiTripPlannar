from pydantic import BaseModel, Field


class ItineraryDay(BaseModel):
    day: int = Field(description="Day number starting from 1.")
    title: str = Field(description="Short title for the day.")
    activities: list[str] = Field(default_factory=list, description="Activities planned for this day.")


class TravelRecommendation(BaseModel):
    summary: str = Field(description="Brief summary of the recommended trip.")
    weather_summary: str = Field(description="Relevant weather overview and travel advice.")
    currency_summary: str = Field(description="Relevant currency or pricing summary.")
    itinerary: list[ItineraryDay] = Field(default_factory=list, description="Suggested day-wise itinerary.")
    travel_tips: list[str] = Field(default_factory=list, description="Useful travel recommendations and destination tips.")
    final_recommendation: str = Field(description="Concluding recommendation for the trip.")