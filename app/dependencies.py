from functools import lru_cache

from app.services.travel_service import TravelService


@lru_cache
def get_travel_service() -> TravelService:
    """Return the TravelService instance."""
    return TravelService()