"""Activity schemas."""

from typing import Annotated

from pydantic import BaseModel, Field


class PlaceSummary(BaseModel):
    """Basic information returned by place search."""

    name: Annotated[str, Field(description="Name of the place or attraction.")]
    category: Annotated[str | None, Field(default=None, description="Primary place category, such as Museum, Park, or Tourist Attraction.")]
    rating: Annotated[float | None, Field(default=None, description="Average visitor rating based on customer reviews.")]
    reviews: Annotated[int | None, Field(default=None, description="Total number of visitor reviews available for the place.")]
    address: Annotated[str | None, Field(default=None, description="Full address or location of the place.")]
    description: Annotated[str | None, Field(default=None, description="Short description or summary returned by TripAdvisor search.")]
    price: Annotated[float | None, Field(default=None, description="Price of the activity or attraction.")]
    currency: Annotated[str | None, Field(default=None, description="ISO 4217 currency code of the activity price.")]


class RecommendedActivity(BaseModel):
    """Activity selected by the Activity Agent."""

    activity: PlaceSummary
    reason: Annotated[str, Field(description="Reason this activity was selected.")]


class ActivitySelection(BaseModel):
    """Small LLM decision over already retrieved activities."""

    selected_indices: list[int] = Field(
        default_factory=list,
        description="Indexes of selected activities from the supplied list, ordered from best to worst.",
    )
    reasons: list[str] = Field(
        default_factory=list,
        description="One concise reason for each selected activity. Must correspond positionally with selected_indices.",
    )


class ActivityAgentResponse(BaseModel):
    """Final structured output of the Activity Agent."""

    recommendations: list[RecommendedActivity] = Field(
        default_factory=list,
        max_length=3,
        description="Up to three recommended activities.",
    )