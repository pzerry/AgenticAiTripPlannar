from fastapi import APIRouter

from app.api.health import router as health_router
from app.api.travel import router as travel_router

router = APIRouter()

router.include_router(health_router)
router.include_router(travel_router)