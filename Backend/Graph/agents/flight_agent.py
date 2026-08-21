"""Flight specialist agent."""

import json

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from Backend.Exceptions.exception import GraphStateError
from Backend.Graph.state import TravelAgentState
from Backend.LLM.factory import get_llm
from Backend.Logger.decorators import log_agent
from Backend.Logger.logger import get_logger
from Backend.Prompts.utils.prompt_loader import load_prompt
from Backend.Schemas.flight_schema import (
    FlightAgentResponse,
    FlightSelection,
    RecommendedFlight,
)
from Backend.tools.flight_tool import search_flights
from Backend.integrations.flight_client import flight_client


logger = get_logger(__name__)


llm = get_llm("groq")

structured_llm = llm.with_structured_output(
    FlightSelection
)


async def _resolve_airports(
    plan,
) -> tuple[str, str]:
    """Resolve origin and destination city names to airport IATA codes."""

    if not plan.origin:
        raise GraphStateError(
            "Flight search requires origin."
        )

    if not plan.destination:
        raise GraphStateError(
            "Flight search requires destination."
        )

    try:
        origin_airport, destination_airport = (
            await flight_client.resolve_airports(
                origin=plan.origin,
                destination=plan.destination,
            )
        )

    except Exception as exc:
        raise GraphStateError(
            f"Unable to resolve airports for "
            f"{plan.origin} -> {plan.destination}: {exc}"
        ) from exc

    if not origin_airport:
        raise GraphStateError(
            f"Could not resolve origin airport for "
            f"{plan.origin}."
        )

    if not destination_airport:
        raise GraphStateError(
            f"Could not resolve destination airport for "
            f"{plan.destination}."
        )

    logger.info(
        "Resolved flight route: %s -> %s",
        origin_airport,
        destination_airport,
    )

    return (
        origin_airport,
        destination_airport,
    )


def _build_flight_query(
    plan,
    origin_airport: str,
    destination_airport: str,
) -> dict:
    """Build the flight search tool input."""

    if not plan.departure_date:
        raise GraphStateError(
            "Flight search requires departure_date."
        )

    return {
        "origin": origin_airport,
        "destination": destination_airport,
        "departure_date": plan.departure_date,
        "return_date": plan.return_date,
        "adults": plan.adults or 1,
        "currency": "USD",
    }


@log_agent("FlightAgent")
async def flight_agent(
    state: TravelAgentState,
    config: RunnableConfig,
) -> dict:
    """Find flights and let the LLM select the best options."""

    try:
        plan = state.get(
            "travel_plan"
        )

        if plan is None:
            raise GraphStateError(
                "Flight Agent requires travel_plan."
            )

        # ==================================================
        # Airport resolution
        # ==================================================

        origin_airport, destination_airport = (
            await _resolve_airports(plan)
        )

        # ==================================================
        # Flight search
        # ==================================================

        tool_input = _build_flight_query(
            plan,
            origin_airport,
            destination_airport,
        )

        logger.info(
            "Searching flights: %s",
            tool_input,
        )

        flights = await search_flights.ainvoke(
            tool_input,
            config=config,
        )

        if not flights:
            logger.info(
                "No flights found for %s -> %s.",
                origin_airport,
                destination_airport,
            )

            return {
                "flight_recommendations": []
            }

        logger.info(
            "Flight search returned %d options.",
            len(flights),
        )

        # ==================================================
        # Small LLM decision
        # ==================================================

        flights_data = [
            {
                "index": index,
                **flight,
            }
            for index, flight in enumerate(flights)
        ]

        flight_json = json.dumps(
            flights_data,
            indent=2,
            ensure_ascii=False,
        )

        selection_prompt = (
            "Travel Plan:\n"
            f"{plan.model_dump_json(indent=2)}\n\n"
            "Resolved Airports:\n"
            f"Origin airport: {origin_airport}\n"
            f"Destination airport: {destination_airport}\n\n"
            "Available Flights:\n"
            f"{flight_json}\n\n"
            "Select the best flight options from the supplied list.\n"
            "Return the indexes of the selected flights and one reason "
            "for each selected flight."
        )

        logger.info(
            "FlightAgent: starting selection LLM."
        )

        selection: FlightSelection = (
            await structured_llm.ainvoke(
                [
                    SystemMessage(
                        content=load_prompt(
                            "flight_agent.md"
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
            "FlightAgent: selection LLM completed."
        )

        # ==================================================
        # Convert LLM decision → existing Pydantic models
        # ==================================================

        recommendations: list[
            RecommendedFlight
        ] = []

        if len(selection.selected_indices) != len(
            selection.reasons
        ):
            raise GraphStateError(
                "Flight selection indexes and reasons "
                "must have the same length."
            )

        for index, reason in zip(
            selection.selected_indices,
            selection.reasons,
        ):

            if index < 0 or index >= len(flights):
                raise GraphStateError(
                    f"Flight selection index {index} "
                    f"is out of range."
                )

            recommendations.append(
                RecommendedFlight(
                    flight=flights[index],
                    reason=reason,
                )
            )

        # Optional safety limit
        recommendations = recommendations[:3]

        logger.info(
            "FlightAgent returning %d recommendations.",
            len(recommendations),
        )

        # ==================================================
        # Final application output
        # ==================================================

        response = FlightAgentResponse(
            recommendations=recommendations
        )

        return {
            "flight_recommendations": (
                response.recommendations
            )
        }

    except Exception:
        logger.exception(
            "Flight Agent failed."
        )
        raise