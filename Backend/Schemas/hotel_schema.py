from typing import Annotated

from pydantic import BaseModel, Field, HttpUrl


class HotelOption(BaseModel):
    """Structured hotel offer."""

    name: Annotated[str, Field(description="Name of the hotel or accommodation.")]
    price_per_night: Annotated[float | None, Field(default=None, description="Nightly room rate.")]
    total_price: Annotated[float | None, Field(default=None, description="Total price for the selected stay.")]
    currency: Annotated[str, Field(description="Three-letter ISO currency code (e.g., USD, INR, EUR).")]
    rating: Annotated[float | None, Field(default=None, description="Average guest rating.")]
    reviews: Annotated[int | None, Field(default=None, description="Total number of guest reviews.")]
    hotel_class: Annotated[str | None, Field(default=None, description="Hotel classification such as 3-star, 4-star, or 5-star.")]
    address: Annotated[str | None, Field(default=None, description="Hotel address.")]
    amenities: Annotated[list[str] | None, Field(default=None, description="List of available hotel amenities.")]
    check_in_time: Annotated[str | None, Field(default=None, description="Hotel check-in time.")]
    check_out_time: Annotated[str | None, Field(default=None, description="Hotel check-out time.")]
    free_cancellation: Annotated[bool | None, Field(default=None, description="Whether free cancellation is available.")]

from pydantic import BaseModel, Field


class HotelSelection(BaseModel):
    """LLM selection over already retrieved hotels."""

    selected_indices: list[int] = Field(
        description=(
            "Indexes of the selected hotels from the supplied hotel list."
        )
    )

    reasons: list[str] = Field(
        description=(
            "Reason for each selected hotel, in the same order "
            "as selected_indices."
        )
    )

    
class RecommendedHotel(BaseModel):
    hotel: HotelOption
    reason: Annotated[str, Field(description="Reason this hotel was selected.")]


class HotelAgentResponse(BaseModel):
    recommendations: Annotated[list[RecommendedHotel], Field(description="Best hotel recommendations for the travel plan.")]