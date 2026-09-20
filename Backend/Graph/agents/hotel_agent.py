"""Hotel specialist agent."""

import json

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from Backend.Exceptions.exception import GraphStateError
from Backend.Graph.state import TravelAgentState
from Backend.LLM.factory import get_llm
from Backend.Logger.decorators import log_agent
from Backend.Logger.logger import get_logger
from Backend.Prompts.utils.prompt_loader import load_prompt
from Backend.Schemas.hotel_schema import (
    HotelSelection,
    RecommendedHotel,
)
from Backend.tools.hotel_tool import search_hotels


logger = get_logger(__name__)


llm = get_llm("groq")

structured_llm = llm.with_structured_output(
    HotelSelection
)


@log_agent("HotelAgent")
async def hotel_agent(
    state: TravelAgentState,
    config: RunnableConfig,
) -> dict:
    """Find hotels and let the LLM select the best options."""

    try:

        # ==================================================
        # Travel Plan
        # ==================================================

        plan = state.get(
            "travel_plan"
        )

        if plan is None:
            raise GraphStateError(
                "Hotel Agent requires travel_plan."
            )

        if not plan.destination:
            raise GraphStateError(
                "Hotel search requires destination."
            )

        if not plan.departure_date:
            raise GraphStateError(
                "Hotel search requires check-in date."
            )

        if not plan.return_date:
            raise GraphStateError(
                "Hotel search requires check-out date."
            )

        # ==================================================
        # Hotel Search
        # ==================================================

        logger.info(
            "Searching hotels for %s.",
            plan.destination,
        )

        hotels = await search_hotels.ainvoke(
            {
                "destination": plan.destination,
                "check_in_date": plan.departure_date,
                "check_out_date": plan.return_date,
                "adults": plan.adults or 1,
            },
            config=config,
        )

        if not hotels:

            logger.info(
                "No hotels found for %s.",
                plan.destination,
            )

            return {
                "hotel_recommendations": []
            }

        logger.info(
            "Hotel search returned %d options.",
            len(hotels),
        )

        # ==================================================
        # Prepare small LLM selection input
        # ==================================================

        hotels_data = [
            {
                "index": index,
                **hotel,
            }
            for index, hotel in enumerate(hotels)
        ]

        hotel_json = json.dumps(
            hotels_data,
            indent=2,
            ensure_ascii=False,
        )

        selection_prompt = (
            "Travel Plan:\n"
            f"{plan.model_dump_json(indent=2)}\n\n"

            "Available Hotels:\n"
            f"{hotel_json}\n\n"

            "Select the best hotel options from the supplied list.\n"
            "Return the indexes of the selected hotels and one reason "
            "for each selected hotel."
        )

        # ==================================================
        # Small LLM Decision
        # ==================================================

        logger.info(
            "HotelAgent: starting selection LLM."
        )

        selection: HotelSelection = (
            await structured_llm.ainvoke(
                [
                    SystemMessage(
                        content=load_prompt(
                            "hotel_agent.md"
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
            "HotelAgent: selection LLM completed."
        )

        if selection is None:
            raise GraphStateError(
                "Hotel selection returned no response."
            )

        # ==================================================
        # Validate LLM selection
        # ==================================================

        if len(
            selection.selected_indices
        ) != len(
            selection.reasons
        ):
            raise GraphStateError(
                "Hotel selection indexes and reasons "
                "must have the same length."
            )

        # ==================================================
        # Convert LLM decision back to Pydantic models
        # ==================================================

        recommendations: list[
            RecommendedHotel
        ] = []

        for index, reason in zip(
            selection.selected_indices,
            selection.reasons,
        ):

            if index < 0 or index >= len(hotels):
                raise GraphStateError(
                    f"Hotel selection index {index} "
                    f"is out of range."
                )

            recommendations.append(
                RecommendedHotel(
                    hotel=hotels[index],
                    reason=reason,
                )
            )

        # Keep at most 3 recommendations.
        recommendations = recommendations[:3]

        logger.info(
            "HotelAgent returning %d recommendations.",
            len(recommendations),
        )

        return {
            "hotel_recommendations": recommendations
        }

    except Exception:
        logger.exception(
            "Hotel Agent failed."
        )
        raise