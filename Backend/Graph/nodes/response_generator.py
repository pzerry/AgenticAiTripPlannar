import json

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from Backend.Graph.state import TravelAgentState
from Backend.Graph.budget import build_budget, insert_budget
from Backend.LLM.factory import get_llm
from Backend.Logger.decorators import log_agent
from Backend.Logger.logger import get_logger
from Backend.Prompts.utils.prompt_loader import load_prompt

logger = get_logger(__name__)
llm = get_llm("openrouter_analyzer")


def serialize(value):
    if value is None:
        return None
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return value


@log_agent("ResponseGenerator")
async def response_generator(state: TravelAgentState, config: RunnableConfig) -> dict:
    execution_plan = state.get("execution_plan")
    intent = execution_plan.intent.value if execution_plan is not None else None

    payload = {
        "intent": intent,
        "travel_plan": serialize(state.get("travel_plan")),
        "flight_recommendations": [serialize(flight) for flight in (state.get("flight_recommendations") or [])],
        "hotel_recommendations": [serialize(hotel) for hotel in (state.get("hotel_recommendations") or [])],
        "activity_recommendations": [serialize(activity) for activity in (state.get("activity_recommendations") or [])],
        "weather": serialize(state.get("weather")),
        "currency_request": serialize(state.get("currency_request")),
        "currency": serialize(state.get("currency")),
    }

    budget = None
    if intent == "full_plan":
        # Choose one flight and hotel consistently for the recommendation and
        # budget. Alternatives are not additional purchases to add to the total.
        payload["flight_recommendations"] = payload["flight_recommendations"][:1]
        payload["hotel_recommendations"] = payload["hotel_recommendations"][:1]
        budget = build_budget(payload)
        payload["budget_summary"] = budget

    logger.info("Generating final response for intent: %s", intent)

    response = await llm.ainvoke(
        [
            SystemMessage(content=load_prompt("response_generator.md")),
            HumanMessage(
                content=(
                    "Execution intent:\n"
                    f"{intent}\n\n"
                    "Available travel data:\n"
                    f"{json.dumps(payload, indent=2, ensure_ascii=False)}\n\n"
                    "Generate the final answer appropriate for this intent. "
                    "Use only the supplied data."
                )
            ),
        ],
        config=config,
    )

    if not response or not response.content:
        raise ValueError("Response Generator returned an empty response.")

    final_response = insert_budget(response.content, budget) if budget is not None else response.content
    return {"final_response": final_response}
