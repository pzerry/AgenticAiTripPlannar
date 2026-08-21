from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

from Backend.Schemas.activity_schema import RecommendedActivity
from Backend.Schemas.currency_schema import CurrencyConversion
from Backend.Schemas.flight_schema import RecommendedFlight
from Backend.Schemas.hotel_schema import RecommendedHotel
from Backend.Schemas.orchestrator_schema import ExecutionPlan
from Backend.Schemas.travel_schema import TravelPackage, TravelPlan
from Backend.Schemas.weather_schema import WeatherResponse


class TravelAgentState(TypedDict):
    """Shared state passed between LangGraph nodes."""

    # =========================
    # Conversation
    # =========================
    messages: Annotated[
        list[BaseMessage],
        add_messages,
    ]

    # =========================
    # Request Analysis
    # =========================
    clarification_required: bool
    clarification_questions: list[str]
    travel_plan: TravelPlan | None
    user_preferences: str | None

    # =========================
    # Memory
    # =========================
    memory_context: dict | None

    # =========================
    # Orchestration
    # =========================
    execution_plan: ExecutionPlan | None

    # =========================
    # Agent Outputs
    # =========================
    flight_recommendations: list[RecommendedFlight] | None
    hotel_recommendations: list[RecommendedHotel] | None
    activity_recommendations: list[RecommendedActivity] | None

    # =========================
    # Supporting Data Nodes
    # =========================
    weather: WeatherResponse | None
    currency: CurrencyConversion | None

    # =========================
    # Package Generation
    # =========================
    travel_packages: list[TravelPackage] | None

    # =========================
    # Final Response
    # =========================
    final_response: str | None