import json

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from Backend.Graph.state import TravelAgentState
from Backend.LLM.factory import get_llm
from Backend.Logger.decorators import log_agent
from Backend.Prompts.utils.prompt_loader import load_prompt
from Backend.Logger.logger import get_logger
from Backend.Schemas.travel_schema import TravelPackagesResponse

logger = get_logger(__name__)
llm = get_llm("ollama_qwen3")
logger.info("PackageAgent STARTED")
structured_llm = llm.with_structured_output(
    TravelPackagesResponse
)


@log_agent("PackageAgent")
async def package_agent(
    state: TravelAgentState,
    config: RunnableConfig,
) -> dict:
    """
    Select travel packages from the available flight,
    hotel, activity, and weather results.

    Currency conversion is handled separately.
    """
    logger.info("PackageAgent STARTED")
    travel_plan = state.get("travel_plan")

    if travel_plan is None:
        raise ValueError(
            "Package Agent requires travel_plan."
        )

    flights = state.get(
        "flight_recommendations",
        [],
    )

    hotels = state.get(
        "hotel_recommendations",
        [],
    )

    activities = state.get(
        "activity_recommendations",
        [],
    )

    weather = state.get(
        "weather"
    )

    # ---------------------------------------------
    # Prepare JSON-safe input
    # ---------------------------------------------

    flights_data = [
        flight.model_dump(mode="json")
        for flight in flights
    ]

    hotels_data = [
        hotel.model_dump(mode="json")
        for hotel in hotels
    ]

    activities_data = [
        activity.model_dump(mode="json")
        for activity in activities
    ]

    if hasattr(weather, "model_dump"):
        weather_data = weather.model_dump(
            mode="json"
        )
    else:
        weather_data = weather

    # ---------------------------------------------
    # Build package input
    # ---------------------------------------------

    package_input = (
        "Travel Plan:\n"
        f"{travel_plan.model_dump_json(indent=2)}\n\n"

        "Flights:\n"
        f"{json.dumps(flights_data, indent=2, ensure_ascii=False)}\n\n"

        "Hotels:\n"
        f"{json.dumps(hotels_data, indent=2, ensure_ascii=False)}\n\n"

        "Activities:\n"
        f"{json.dumps(activities_data, indent=2, ensure_ascii=False)}\n\n"

        "Weather:\n"
        f"{json.dumps(weather_data, indent=2, ensure_ascii=False)}"
    )

    # ---------------------------------------------
    # LLM package selection
    # ---------------------------------------------

    response = await structured_llm.ainvoke(
        [
            SystemMessage(
                content=load_prompt(
                    "packet_generator.md"
                )
            ),
            HumanMessage(
                content=package_input
            ),
        ],
        config=config,
    )

    if response is None:
        raise ValueError(
            "Package Agent returned no response."
        )

    return {
        "travel_packages": response.travel_packages,
    }