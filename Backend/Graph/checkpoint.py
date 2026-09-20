"""Explicit types that may be restored from a persisted travel checkpoint."""

from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

from Backend.Schemas.activity_schema import PlaceSummary, RecommendedActivity
from Backend.Schemas.currency_schema import CurrencyConversion, CurrencyRequest
from Backend.Schemas.flight_schema import FlightOption, RecommendedFlight
from Backend.Schemas.hotel_schema import HotelOption, RecommendedHotel
from Backend.Schemas.orchestrator_schema import ExecutionPlan, TravelIntent, WorkerType
from Backend.Schemas.travel_schema import TravelPlan
from Backend.Schemas.weather_schema import WeatherResponse


def checkpoint_serializer() -> JsonPlusSerializer:
    # LangGraph already permits its standard messages and built-in types. Add
    # only our persisted models, rather than allowing arbitrary Python classes.
    types = (
        TravelPlan, ExecutionPlan, TravelIntent, WorkerType,
        FlightOption, RecommendedFlight, HotelOption, RecommendedHotel,
        PlaceSummary, RecommendedActivity, CurrencyConversion, CurrencyRequest,
        WeatherResponse,
    )
    return JsonPlusSerializer(allowed_msgpack_modules=types, pickle_fallback=False)
