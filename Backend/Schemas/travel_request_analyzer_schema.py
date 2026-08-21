from pydantic import BaseModel, Field


class TravelPlanUpdates(BaseModel):
    """Only values newly learned or changed in the current turn."""

    origin: str | None = None
    origin_country: str | None = None
    origin_currency: str | None = None
    origin_airport: str | None = None

    destination: str | None = None
    destination_country: str | None = None
    destination_currency: str | None = None
    destination_airport: str | None = None

    departure_date: str | None = None
    return_date: str | None = None
    duration_days: int | None = None

    adults: int | None = None
    travel_class: str | None = None

    departure_time_pref: str | None = None
    arrival_time_pref: str | None = None

    total_budget: float | None = None
    budget_currency: str | None = None


class TravelRequestAnalyzerOutput(BaseModel):
    """Structured output of the Travel Request Analyzer."""

    updates: TravelPlanUpdates = Field(
        description=(
            "Only travel fields newly learned or changed "
            "in the current turn."
        )
    )

    clarification_required: bool = Field(
        default=False,
    )

    clarification_questions: list[str] = Field(
        default_factory=list,
        description=(
            "Zero, one, or multiple clarification questions. "
            "Return an empty list when no clarification is required."
        ),
    )