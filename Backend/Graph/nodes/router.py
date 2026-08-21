"""Graph routing for the AI Travel Planner."""

from typing import Literal

from langgraph.types import Send

from Backend.Exceptions.exception import RoutingError
from Backend.Graph.state import TravelAgentState
from Backend.Logger.logger import get_logger
from Backend.Schemas.orchestrator_schema import WorkerType


logger = get_logger(__name__)


ROUTES: dict[WorkerType, str] = {
    WorkerType.FLIGHT: "flight_agent",
    WorkerType.HOTEL: "hotel_agent",
    WorkerType.ACTIVITY: "activity_agent",
    WorkerType.WEATHER: "weather_node",
    WorkerType.CURRENCY: "currency_node",

}


def analyzer_router(
    state: TravelAgentState,
) -> Literal["orchestrator", "__end__"]:
    """
    Route execution after the Travel Request Analyzer.

    If clarification is required, stop the current graph execution.
    Otherwise continue to the Orchestrator.
    """

    if state.get(
        "clarification_required",
        False,
    ):
        return "__end__"

    return "orchestrator"


def fanout(
    state: TravelAgentState,
) -> list[Send]:
    """
    Fan out workers selected by the Orchestrator.
    """

    execution_plan = state.get("execution_plan")

    if execution_plan is None:
        raise RoutingError(
            "Execution plan is missing."
        )

    workers = execution_plan.workers

    if not workers:
        raise RoutingError(
            "Execution plan must contain at least one worker."
        )

    sends: list[Send] = []
    seen: set[WorkerType] = set()

    for worker in workers:

        if worker in seen:
            raise RoutingError(
                f"Duplicate worker in execution plan: {worker}"
            )

        seen.add(worker)

        route = ROUTES.get(worker)

        if route is None:
            raise RoutingError(
                f"No graph route exists for worker: {worker}"
            )

        sends.append(
            Send(
                route,
                state,
            )
        )

    logger.info(
        "Fanout created %d worker executions: %s",
        len(sends),
        [worker.value for worker in workers],
    )

    return sends