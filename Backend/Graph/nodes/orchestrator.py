"""Orchestrator node."""

import json

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from Backend.Exceptions.exception import GraphStateError
from Backend.Graph.state import TravelAgentState
from Backend.LLM.factory import get_llm
from Backend.Logger.decorators import log_agent
from Backend.Logger.logger import get_logger
from Backend.Prompts.orchestrator_prompt import orchestrator_prompt
from Backend.Schemas.orchestrator_schema import ExecutionPlan


logger = get_logger(__name__)


llm = get_llm("openrouter_analyzer")


@log_agent("Orchestrator")
async def orchestrator(
    state: TravelAgentState,
    config: RunnableConfig,
) -> dict:
    """
    Create the execution plan for the travel workflow.

    Responsibilities:
    - understand the user's requested outcome
    - determine the travel intent
    - determine the required workers
    - create the ExecutionPlan

    Does not:
    - call travel APIs
    - modify TravelPlan
    - generate recommendations
    - execute workers
    - ask clarification questions
    """

    try:
        travel_plan = state.get("travel_plan")

        if travel_plan is None:
            raise GraphStateError(
                "Orchestrator requires a TravelPlan."
            )

        messages = state.get(
            "messages",
            [],
        )

        response = await (
            orchestrator_prompt
            | llm
        ).ainvoke(
            {
                "travel_plan": travel_plan.model_dump(
                    mode="json"
                ),
                "messages": messages,
            },
            config=config,
        )

        raw_content = response.content

        if not raw_content:
            raise GraphStateError(
                "Orchestrator returned empty response."
            )

        logger.info(
            "Raw orchestrator response: %s",
            raw_content,
        )

        # ---------------------------------------------
        # Parse JSON
        # ---------------------------------------------

        try:
            data = json.loads(raw_content)

        except json.JSONDecodeError as exc:
            raise GraphStateError(
                "Orchestrator returned invalid JSON: "
                f"{raw_content}"
            ) from exc

        # ---------------------------------------------
        # Validate with Pydantic
        # ---------------------------------------------

        try:
            result = ExecutionPlan.model_validate(
                data
            )

        except Exception as exc:
            raise GraphStateError(
                "Orchestrator returned invalid execution plan: "
                f"{data}"
            ) from exc

        if not result.workers:
            raise GraphStateError(
                "Orchestrator returned no workers."
            )

        logger.info(
            "Orchestrator intent: %s",
            result.intent,
        )

        logger.info(
            "Orchestrator workers: %s",
            [
                worker.value
                for worker in result.workers
            ],
        )

        return {
            "execution_plan": result,
        }

    except Exception:
        logger.exception(
            "Orchestrator failed."
        )
        raise