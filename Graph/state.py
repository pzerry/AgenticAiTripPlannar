from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

from Schemas.flight_schema import FlightOption
from Schemas.hotel_schema import HotelOption
from Schemas.activity_schema import PlaceSummary
from Schemas.weather_schema import WeatherInfo
from Schemas.currency_schema import CurrencyConversion
from Schemas.travel_schema import TravelPlan, TravelPackage



class TravelAgentState(TypedDict):
    # Conversation
    messages: Annotated[list[BaseMessage], add_messages]

    # Planner Output
    travel_plan: TravelPlan | None

    # Worker Outputs
    flight: list[FlightOption] | None
    hotel: list[HotelOption] | None
    activities: list[PlaceSummary] | None
    weather: WeatherInfo | None
    currency: CurrencyConversion | None

    #final recommendation
    travel_package: TravelPackage | None

    # Final Response
    final_response: str | None

    # System
    errors: list[str]