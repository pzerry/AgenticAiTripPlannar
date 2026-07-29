"""Planner node."""

from Graph.state import TravelAgentState
from Prompts.plannar_prompt import planner_prompt
from Schemas.travel_schema import TravelPlan
from llm.factory import llm


planner_chain = planner_prompt | llm.with_structured_output(TravelPlan)


def planner_node(state: TravelAgentState) -> dict:
    """Extract or update the user's travel plan."""

    existing_plan = (
        state["travel_plan"].model_dump_json(indent=2)
        if state.get("travel_plan")
        else "No existing travel plan."
    )

    updated_plan = planner_chain.invoke(
        {
            "messages": state["messages"],
            "existing_travel_plan": existing_plan,
            "user_preferences": "{}",
        }
    )

    return {
        "travel_plan": updated_plan
    }