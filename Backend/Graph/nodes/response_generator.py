import json

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from Backend.Graph.state import TravelAgentState
from Backend.LLM.factory import get_llm
from Backend.Logger.decorators import log_agent
from Backend.Logger.logger import get_logger
from Backend.Prompts.utils.prompt_loader import load_prompt


logger = get_logger(__name__)
llm = get_llm("openrouter_generator")


def serialize(value):
    """Convert Pydantic objects to JSON-safe data."""
    if value is None:
        return None

    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")

    return value


@log_agent("ResponseGenerator")
async def response_generator(state: TravelAgentState, config: RunnableConfig) -> dict:
    """Generate the final response from available execution results."""
    payload = {
        "travel_plan": serialize(state.get("travel_plan")),
        "travel_packages": serialize(state.get("travel_packages")),
        "flight_recommendations": [
            serialize(flight)
            for flight in (state.get("flight_recommendations") or [])
        ],
        "hotel_recommendations": [
            serialize(hotel)
            for hotel in (state.get("hotel_recommendations") or [])
        ],
        "activity_recommendations": [
            serialize(activity)
            for activity in (state.get("activity_recommendations") or [])
        ],
        "weather": serialize(state.get("weather")),
        "currency": serialize(state.get("currency")),
    }

    logger.info("Generating final response from available results.")

    response = await llm.ainvoke(
        [
            SystemMessage(content=load_prompt("response_generator.md")),
            HumanMessage(
                content=(
                    "Available travel data:\n"
                    f"{json.dumps(payload, indent=2, ensure_ascii=False)}\n\n"
                    "Generate the final answer using only the available data."
                )
            ),
        ],
        config=config,
    )

    return {"final_response": response.content}