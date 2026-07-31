"""Orchestrator node."""

from langchain_core.runnables import RunnableConfig

from llm import llm
from Graph.state import TravelAgentState
from Prompts.orchestrator_prompt import orchestrator_prompt
from Schemas.orchestrator_schema import OrchestratorOutput


structured_llm = llm.with_structured_output(
    OrchestratorOutput
)


async def orchestrator(
    state: TravelAgentState,
    config: RunnableConfig,
) -> TravelAgentState:
    """
    Decide which workers should execute.

    Responsibilities:
    - Analyse the current TravelPlan
    - Produce an ExecutionPlan
    - Decide if Human-in-the-Loop is required

    Does NOT:
    - Modify the TravelPlan
    - Call tools
    - Execute workers
    """

    chain = (
        orchestrator_prompt
        | structured_llm
    )

    result = await chain.ainvoke(
        {
            "travel_plan": state["travel_plan"],
            "user_preferences": state.get(
                "user_preferences",
                "No user preferences available.",
            ),
            "messages": state["messages"],
        },
        config=config,
    )

    return {
        **state,
        "execution_plan": result.execution_plan,
        "hitl_required": result.hitl_required,
        "hitl_reason": result.hitl_reason,
    }