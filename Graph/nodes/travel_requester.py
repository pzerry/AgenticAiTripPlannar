"""Travel Request Analyzer node."""

from langchain_core.runnables import RunnableConfig

from Graph.state import TravelAgentState
from Prompts.travel_request_analyzer_prompt import travel_request_analyzer_prompt
from Schemas.travel_request_analyzer_schema import TravelRequestAnalyzerOutput
from llm import llm


structured_llm = llm.with_structured_output(
    TravelRequestAnalyzerOutput
)


async def travel_request_analyzer(
    state: TravelAgentState,
    config: RunnableConfig,
) -> TravelAgentState:
    """
    Extract structured travel information from the conversation.

    Responsibilities:
    - Read conversation
    - Update TravelPlan
    - Detect clarification requirements

    It does NOT:
    - Decide worker execution
    - Call tools
    - Generate itineraries
    """

    chain = (
        travel_request_analyzer_prompt
        | structured_llm
    )

    result = await chain.ainvoke(
        {
            "travel_plan": state.get("travel_plan"),
            "messages": state["messages"],
        },
        config=config,
    )

    return {
        **state,
        "travel_plan": result.travel_plan,
        "clarification_required": result.clarification_required,
        "clarification_question": result.clarification_question,
    }