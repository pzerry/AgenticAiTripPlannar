"""Activity specialist agent."""

import json

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from Backend.Exceptions.exception import GraphStateError
from Backend.Graph.state import TravelAgentState
from Backend.LLM.factory import get_llm
from Backend.Logger.decorators import log_agent
from Backend.Logger.logger import get_logger
from Backend.Prompts.utils.prompt_loader import load_prompt
from Backend.Schemas.activity_schema import (
    ActivitySelection,
    PlaceSummary,
    RecommendedActivity,
)
from Backend.tools.activity_tool import search_activities


logger = get_logger(__name__)


llm = get_llm("ollama_qwen3")

structured_llm = llm.with_structured_output(
    ActivitySelection
)


@log_agent("ActivityAgent")
async def activity_agent(
    state: TravelAgentState,
    config: RunnableConfig,
) -> dict:
    """Search activities and let the LLM select the best options."""

    try:
        # ==================================================
        # Travel Plan
        # ==================================================

        plan = state.get(
            "travel_plan"
        )

        if plan is None:
            raise GraphStateError(
                "Activity Agent requires travel_plan."
            )

        if not plan.destination:
            raise GraphStateError(
                "Activity search requires destination."
            )

        # ==================================================
        # Activity Search
        # ==================================================

        logger.info(
            "Searching activities for %s.",
            plan.destination,
        )

        activities = await search_activities.ainvoke(
            {
                "query": plan.destination,
                "location": plan.destination,
            },
            config=config,
        )

        if not activities:
            logger.info(
                "No activities found for %s.",
                plan.destination,
            )

            return {
                "activity_recommendations": []
            }

        logger.info(
            "Activity search returned %d options.",
            len(activities),
        )

        # ==================================================
        # Normalize API results → PlaceSummary
        # ==================================================

        normalized_activities: list[
            PlaceSummary
        ] = []

        for activity in activities:

            if isinstance(
                activity,
                PlaceSummary,
            ):
                normalized_activities.append(
                    activity
                )

            elif isinstance(
                activity,
                dict,
            ):
                try:
                    normalized_activities.append(
                        PlaceSummary.model_validate(
                            activity
                        )
                    )

                except Exception as exc:
                    logger.warning(
                        "Skipping invalid activity: %s",
                        exc,
                    )

            else:
                logger.warning(
                    "Skipping unsupported activity type: %s",
                    type(activity).__name__,
                )

        if not normalized_activities:
            logger.info(
                "No valid activities remained after normalization."
            )

            return {
                "activity_recommendations": []
            }

        logger.info(
            "Normalized %d activities.",
            len(normalized_activities),
        )

        # ==================================================
        # Prepare small LLM selection input
        # ==================================================

        activities_data = [
            {
                "index": index,
                **activity.model_dump(
                    mode="json"
                ),
            }
            for index, activity in enumerate(
                normalized_activities
            )
        ]

        activity_json = json.dumps(
            activities_data,
            indent=2,
            ensure_ascii=False,
        )

        selection_prompt = (
            "Travel Plan:\n"
            f"{plan.model_dump_json(indent=2)}\n\n"
            "Available Activities:\n"
            f"{activity_json}\n\n"
            "Select the best activity options from the supplied list.\n"
            "Return the indexes of the selected activities and one "
            "reason for each selected activity.\n"
            "Select at most 3 activities."
        )

        # ==================================================
        # Small LLM Decision
        # ==================================================

        logger.info(
            "ActivityAgent: starting selection LLM."
        )

        selection: ActivitySelection = (
            await structured_llm.ainvoke(
                [
                    SystemMessage(
                        content=load_prompt(
                            "activity_agent.md"
                        )
                    ),
                    HumanMessage(
                        content=selection_prompt
                    ),
                ],
                config=config,
            )
        )

        logger.info(
            "ActivityAgent: selection LLM completed."
        )

        if selection is None:
            raise GraphStateError(
                "Activity selection returned no response."
            )

        # ==================================================
        # Validate LLM Selection
        # ==================================================

        if len(
            selection.selected_indices
        ) != len(
            selection.reasons
        ):
            raise GraphStateError(
                "Activity selection indexes and reasons "
                "must have the same length."
            )

        # ==================================================
        # Convert LLM decision →
        # existing Pydantic models
        # ==================================================

        recommendations: list[
            RecommendedActivity
        ] = []

        seen_indices: set[int] = set()

        for index, reason in zip(
            selection.selected_indices,
            selection.reasons,
        ):

            # ----------------------------------------------
            # Duplicate protection
            # ----------------------------------------------

            if index in seen_indices:
                logger.warning(
                    "Ignoring duplicate activity index %d.",
                    index,
                )
                continue

            # ----------------------------------------------
            # Index validation
            # ----------------------------------------------

            if (
                index < 0
                or index >= len(
                    normalized_activities
                )
            ):
                raise GraphStateError(
                    f"Activity selection index {index} "
                    f"is out of range."
                )

            seen_indices.add(
                index
            )

            # ----------------------------------------------
            # Preserve original PlaceSummary
            # ----------------------------------------------

            recommendations.append(
                RecommendedActivity(
                    activity=normalized_activities[
                        index
                    ],
                    reason=reason,
                )
            )

        # ==================================================
        # Safety Limit
        # ==================================================

        recommendations = recommendations[:3]

        # ==================================================
        # Final Application Output
        # ==================================================

        logger.info(
            "ActivityAgent returning %d recommendations.",
            len(recommendations),
        )

        return {
            "activity_recommendations": recommendations,
        }

    except Exception:
        logger.exception(
            "Activity Agent failed."
        )
        raise