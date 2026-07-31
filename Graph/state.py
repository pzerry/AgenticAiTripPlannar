from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

from Schemas.activity_schema import PlaceSummary
from Schemas.currency_schema import CurrencyConversion
from Schemas.flight_schema import FlightOption
from Schemas.hotel_schema import HotelOption
from Schemas.travel_schema import TravelPackage, TravelPlan
from Schemas.weather_schema import WeatherInfo
from Schemas.orchestrator_schema import ExecutionPlan


class TravelAgentState(TypedDict):
    """Shared state passed between all LangGraph nodes."""

    # =========================
    # Conversation
    # =========================
    messages: Annotated[list[BaseMessage], add_messages]

    # =========================
    # Travel_Request analyzing
    # =========================
    clarification_required: bool
    clarification_question: str | None

    # =========================
    # Orchestrator Output
    # =========================
    travel_plan: TravelPlan | None
    execution_plan: ExecutionPlan | None

    # =========================
    # Worker Outputs
    # =========================
    flight: list[FlightOption] | None
    hotel: list[HotelOption] | None
    activities: list[PlaceSummary] | None
    weather: WeatherInfo | None
    currency: CurrencyConversion | None

    # =========================
    # Package Generation
    # =========================
    travel_packages: list[TravelPackage] | None

    # =========================
    # Final Response
    # =========================
    final_response: str | None

    # =========================
    # Runtime
    # =========================
    errors: list[dict]