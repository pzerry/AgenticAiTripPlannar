from typing import Annotated

from pydantic import BaseModel, Field, HttpUrl


class HotelOption(BaseModel):
    """Structured hotel offer."""

    name: Annotated[str, Field(description="Name of the hotel or accommodation.")]
    price_per_night: Annotated[
    float | None,
    Field(
        default=None,
        description="Nightly room rate as a numeric value."
    )]
    total_price: Annotated[
    float | None,
    Field(
        default=None,
        description="Total cost for the selected stay."
    )
]
    rating: Annotated[float | None, Field(default=None, description="Average guest rating based on customer reviews.")]
    reviews: Annotated[int | None, Field(default=None, description="Total number of verified guest reviews.")]
    hotel_class: Annotated[
    str | None,
    Field(
        default=None,
        description="Hotel classification such as '2-star hotel'."
    )
]
    address: Annotated[str | None, Field(default=None, description="Complete address or location of the hotel.")]
    thumbnail: Annotated[HttpUrl | None, Field(default=None, description="URL of the primary image representing the hotel.")]
    amenities: Annotated[
    list[str] | None,
    Field(
        default=None,
        description="List of facilities and services available at the hotel, such as Wi-Fi, parking, pool, or breakfast."
    ),
] 
    check_in_time: Annotated[str | None, Field(default=None, description="Scheduled check-in time provided by the hotel.")]
    check_out_time: Annotated[str | None, Field(default=None, description="Scheduled check-out time provided by the hotel.")]
    booking_link: Annotated[HttpUrl | None, Field(default=None, description="Direct URL to the hotel's booking or reservation page.")]
    source: Annotated[str, Field(default="Google Hotels", description="Source from which the hotel information was retrieved.")]
    free_cancellation: Annotated[
    bool | None,
    Field(
        default=None,
        description="Whether the displayed rate offers free cancellation."
    )
]