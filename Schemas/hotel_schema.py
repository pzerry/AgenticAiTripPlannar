from typing import Annotated

from pydantic import BaseModel, Field


class HotelOption(BaseModel):
    """Structured hotel offer."""

    name: Annotated[str, Field(description="Hotel name.")]
    price_per_night: Annotated[str, Field(description="Displayed nightly room price.")]
    rating: Annotated[float | None, Field(default=None, description="Average guest rating.")]
    reviews: Annotated[int | None, Field(default=None, description="Number of guest reviews.")]
    hotel_class: Annotated[int | None, Field(default=None, description="Hotel star classification.")]
    address: Annotated[str | None, Field(default=None, description="Hotel address.")]
    source: Annotated[str, Field(description="Source of hotel information.")]