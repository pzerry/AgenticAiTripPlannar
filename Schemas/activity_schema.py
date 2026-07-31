"""Activity schemas."""

from typing import Annotated
from pydantic import BaseModel, Field, HttpUrl


class PlaceSummary(BaseModel):
    """Basic information returned by place search."""

    place_id: Annotated[str, Field(description="Unique TripAdvisor identifier for the place.")]
    name: Annotated[str, Field(description="Name of the place or attraction.")]
    category: Annotated[str | None, Field(default=None, description="Primary place category, such as Restaurant, Museum, Park, or Tourist Attraction.")]
    rating: Annotated[float | None, Field(default=None, description="Average visitor rating based on customer reviews.")]
    reviews: Annotated[int | None, Field(default=None, description="Total number of visitor reviews available for the place.")]
    address: Annotated[str | None, Field(default=None, description="Full address or location of the place.")]
    description: Annotated[str | None, Field(default=None, description="Short description or summary returned by TripAdvisor search.")]
    thumbnail: Annotated[HttpUrl | None, Field(default=None, description="URL of a representative image for the place.")]