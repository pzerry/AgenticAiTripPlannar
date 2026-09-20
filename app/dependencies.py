from fastapi import Request

from app.services.travel_service import TravelService


def get_travel_service(request: Request) -> TravelService:
    """Return the application-wide TravelService instance."""

    return request.app.state.travel_service