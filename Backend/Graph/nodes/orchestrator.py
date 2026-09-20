"""Choose the travel workers using a validated model response."""

from functools import lru_cache

from langchain_core.exceptions import OutputParserException
from langchain_core.runnables import RunnableConfig

from Backend.Exceptions.exception import GraphStateError
from Backend.Graph.state import TravelAgentState
from Backend.Logger.decorators import log_agent
from Backend.Logger.logger import get_logger
from Backend.Prompts.orchestrator_prompt import orchestrator_prompt
from Backend.Schemas.orchestrator_schema import ExecutionPlan

logger = get_logger(__name__)


@lru_cache(maxsize=1)
def get_orchestrator_chain():
    from Backend.LLM.factory import get_llm

    # Ask the provider for JSON instead of ordinary chat text. LangChain's
    # Pydantic parser also handles a JSON Markdown fence if one is returned,
    # and validates intent/workers before the graph dispatches any travel APIs.
    return orchestrator_prompt | get_llm("groq").with_structured_output(
        ExecutionPlan, method="json_mode"
    )


@log_agent("Orchestrator")
async def orchestrator(state: TravelAgentState, config: RunnableConfig) -> dict:
    """Create an ExecutionPlan without changing the trip or executing workers."""
    travel_plan = state.get("travel_plan")
    if travel_plan is None:
        raise GraphStateError("Orchestrator requires a TravelPlan.")

    try:
        result = await get_orchestrator_chain().ainvoke(
            {
                "travel_plan": travel_plan.model_dump(mode="json"),
                "messages": state.get("messages", []),
            },
            config=config,
        )
    except OutputParserException:
        # Do not copy raw model text into errors or routine logs. Invalid JSON,
        # unknown intent/worker values, and empty worker lists must fail closed.
        raise GraphStateError("Orchestrator returned an invalid execution plan.") from None

    logger.info("Orchestrator intent: %s", result.intent.value)
    logger.info("Orchestrator workers: %s", [worker.value for worker in result.workers])
    return {"execution_plan": result}
