from enum import Enum

from pydantic import BaseModel, Field


class WorkerType(str, Enum):
    FLIGHT = "FLIGHT"
    HOTEL = "HOTEL"
    ACTIVITY = "ACTIVITY"
    WEATHER = "WEATHER"
    CURRENCY = "CURRENCY"


class TravelIntent(str, Enum):
    FULL_PLAN = "full_plan"
    FLIGHTS_ONLY = "flights_only"
    HOTELS_ONLY = "hotels_only"
    ACTIVITIES_ONLY = "activities_only"
    WEATHER_ONLY = "weather_only"
    CURRENCY_ONLY = "currency_only"


class ExecutionPlan(BaseModel):
    intent: TravelIntent = Field(
        description="The user's requested travel service."
    )

    workers: list[WorkerType] = Field(
        min_length=1,
        description="Workers required for the request.",
    )