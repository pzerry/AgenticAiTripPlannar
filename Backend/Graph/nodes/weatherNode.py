"""Weather graph node."""

from langchain_core.runnables import RunnableConfig

from Backend.Exceptions.exception import GraphStateError
from Backend.Graph.state import TravelAgentState
from Backend.tools.weather_tool import get_current_weather


async def weather_node(
    state: TravelAgentState,
    config: RunnableConfig,
) -> dict:
    """
    Fetch current weather for the travel destination.

    Weather is deterministic supporting data and does not use an LLM.
    """

    travel_plan = state.get(
        "travel_plan"
    )

    if travel_plan is None:
        raise GraphStateError(
            "Weather node requires travel_plan."
        )

    if not travel_plan.destination:
        raise GraphStateError(
            "Weather search requires destination."
        )

    weather = await get_current_weather.ainvoke(
        {
            "city": travel_plan.destination,
        },
        config=config,
    )

    return {
        "weather": weather,
    }