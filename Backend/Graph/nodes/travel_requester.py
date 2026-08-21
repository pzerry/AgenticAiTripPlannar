"""Travel Request Analyzer node."""

from datetime import datetime
from zoneinfo import ZoneInfo

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.types import interrupt

from Backend.Graph.state import TravelAgentState
from Backend.LLM.factory import get_llm
from Backend.Logger.decorators import log_agent
from Backend.Logger.logger import get_logger
from Backend.Prompts.travel_request_analyzer_prompt import (
    travel_request_analyzer_prompt,
)
from Backend.Schemas.travel_request_analyzer_schema import (
    TravelRequestAnalyzerOutput,
)
from Backend.Schemas.travel_schema import TravelPlan


logger = get_logger(__name__)

TIMEZONE = "Asia/Kolkata"


llm = get_llm("groq")

structured_llm = llm.with_structured_output(
    TravelRequestAnalyzerOutput,
    method="json_mode",
)

travel_request_chain = (
    travel_request_analyzer_prompt
    | structured_llm
)


def merge_travel_plan(
    current_plan: TravelPlan | None,
    updates: TravelRequestAnalyzerOutput,
) -> TravelPlan:
    """
    Merge only fields returned by the Analyzer
    into the existing TravelPlan.
    """

    if current_plan is None:
        current_plan = TravelPlan()

    update_data = updates.updates.model_dump(
        exclude_none=True,
    )

    if not update_data:
        return current_plan

    current_data = current_plan.model_dump()

    current_data.update(update_data)

    return TravelPlan.model_validate(
        current_data,
    )


@log_agent("travel_request_analyzer")
async def travel_request_analyzer(
    state: TravelAgentState,
    config: RunnableConfig,
) -> dict:
    """
    Analyze the current conversation and progressively
    build the TravelPlan.

    Responsibilities:
    - extract travel information
    - merge new information into TravelPlan
    - determine whether clarification is required
    - ask one or more required clarification questions together
    - resume after the user's clarification response
    """

    now = datetime.now(
        ZoneInfo(TIMEZONE)
    )

    travel_plan = state.get(
        "travel_plan"
    )

    messages = list(
        state.get(
            "messages",
            [],
        )
    )

    try:
        while True:

            # ==================================================
            # Call Analyzer
            # ==================================================

            result: TravelRequestAnalyzerOutput = (
                await travel_request_chain.ainvoke(
                    {
                        "travel_plan": (
                            travel_plan.model_dump(
                                mode="json"
                            )
                            if travel_plan is not None
                            else None
                        ),
                        "messages": messages,
                        "today": now.strftime(
                            "%Y-%m-%d"
                        ),
                        "current_datetime": now.isoformat(),
                        "timezone": TIMEZONE,
                    },
                    config=config,
                )
            )

            # ==================================================
            # Normalize questions
            # ==================================================

            questions = [
                str(question).strip()
                for question
                in result.clarification_questions
                if question
                and str(question).strip()
            ]

            # ==================================================
            # Merge travel updates
            # ==================================================

            travel_plan = merge_travel_plan(
                travel_plan,
                result,
            )

            logger.info(
                "Travel plan updated: %s",
                travel_plan.model_dump(
                    mode="json"
                ),
            )

            logger.info(
                "Clarification required: %s",
                result.clarification_required,
            )

            logger.info(
                "Clarification questions: %s",
                questions,
            )

            # ==================================================
            # Completed
            # ==================================================

            if not result.clarification_required:

                return {
                    "travel_plan": travel_plan,
                    "clarification_required": False,
                    "clarification_questions": [],
                }

            # ==================================================
            # Clarification required
            # ==================================================

            if not questions:
                raise ValueError(
                    "Analyzer requested clarification "
                    "but returned no clarification questions."
                )

            logger.info(
                "Interrupting workflow with %d "
                "clarification question(s).",
                len(questions),
            )

            # ==================================================
            # Interrupt
            # ==================================================

            answer = interrupt(
                {
                    "type": "clarification",
                    "questions": questions,
                }
            )

            # ==================================================
            # Validate user answer
            # ==================================================

            if answer is None:
                raise ValueError(
                    "Clarification answer cannot be None."
                )

            answer = str(
                answer
            ).strip()

            if not answer:
                raise ValueError(
                    "Clarification answer cannot be empty."
                )

            # ==================================================
            # Add answer to conversation
            # ==================================================

            messages.append(
                HumanMessage(
                    content=answer
                )
            )

            logger.info(
                "Clarification response received: %s",
                answer,
            )

    except Exception:
        logger.exception(
            "Travel Request Analyzer failed."
        )
        raise