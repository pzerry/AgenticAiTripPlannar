"""Activity schemas."""

from typing import Annotated

from pydantic import BaseModel, Field


class PlaceSummary(BaseModel):
    """Basic information returned by place search."""

    place_id: Annotated[str, Field(description="Unique TripAdvisor place identifier.")]
    name: Annotated[str, Field(description="Place name.")]
    category: Annotated[str | None, Field(default=None, description="Primary place category.")]
    rating: Annotated[float | None, Field(default=None, description="Average user rating.")]
    reviews: Annotated[int | None, Field(default=None, description="Total number of reviews.")]
    address: Annotated[str | None, Field(default=None, description="Formatted address.")]

class NearbyPlace(BaseModel):
    """Nearby hotel, restaurant, or attraction."""

    name: Annotated[str, Field(description="Nearby place name.")]
    place_id: Annotated[str, Field(description="TripAdvisor place identifier.")]
    rating: Annotated[float | None, Field(default=None, description="Average user rating.")]
    reviews: Annotated[int | None, Field(default=None, description="Total number of reviews.")]


class OperatingHours(BaseModel):
    """Operating hours."""

    day: Annotated[str, Field(description="Day of week.")]
    hours: Annotated[str, Field(description="Opening hours.")]

class PlaceDetails(BaseModel):
    """Detailed information for a place."""

    place_id: Annotated[str, Field(description="TripAdvisor place identifier.")]
    name: Annotated[str, Field(description="Place name.")]
    category: Annotated[str | None, Field(default=None, description="Primary place category.")]
    rating: Annotated[float | None, Field(default=None, description="Average user rating.")]
    reviews: Annotated[int | None, Field(default=None, description="Total number of reviews.")]
    address: Annotated[str | None, Field(default=None, description="Formatted address.")]
    website: Annotated[str | None, Field(default=None, description="Official website URL.")]
    phone: Annotated[str | None, Field(default=None, description="Contact phone number.")]
    description: Annotated[str | None, Field(default=None, description="Review summary or description.")]
    opening_hours: Annotated[list[OperatingHours], Field(default_factory=list, description="Operating hours by day.")]
    images: Annotated[list[str], Field(default_factory=list, description="Image URLs.")]
    nearby_hotels: Annotated[list[NearbyPlace], Field(default_factory=list, description="Nearby hotels.")]
    nearby_restaurants: Annotated[list[NearbyPlace], Field(default_factory=list, description="Nearby restaurants.")]
    nearby_attractions: Annotated[list[NearbyPlace], Field(default_factory=list, description="Nearby attractions.")]