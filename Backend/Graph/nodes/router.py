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

PRICING_WORKERS: set[WorkerType] = {
    WorkerType.FLIGHT,
    WorkerType.HOTEL,
    WorkerType.ACTIVITY,
}


def analyzer_router(state: TravelAgentState) -> Literal["orchestrator", "clarification"]:
    if state.get("clarification_required", False):
        return "clarification"
    return "orchestrator"


def fanout(state: TravelAgentState) -> list[Send]:
    execution_plan = state.get("execution_plan")
    if execution_plan is None:
        raise RoutingError("Execution plan is missing.")

    workers = execution_plan.workers
    if not workers:
        raise RoutingError("Execution plan must contain at least one worker.")

    seen: set[WorkerType] = set()
    for worker in workers:
        if worker in seen:
            raise RoutingError(f"Duplicate worker in execution plan: {worker}")
        seen.add(worker)

    if workers == [WorkerType.CURRENCY]:
        return [Send(ROUTES[WorkerType.CURRENCY], state)]

    sends: list[Send] = []
    for worker in workers:
        if worker == WorkerType.CURRENCY:
            continue
        route = ROUTES.get(worker)
        if route is None:
            raise RoutingError(f"No graph route exists for worker: {worker}")
        sends.append(Send(route, state))

    if not sends:
        raise RoutingError("No executable workers found in execution plan.")

    logger.info(
        "Fanout created %d worker executions: %s",
        len(sends),
        [worker.value for worker in workers if worker != WorkerType.CURRENCY],
    )
    return sends


def worker_router(state: TravelAgentState) -> Literal["currency_node", "response_generator"]:
    execution_plan = state.get("execution_plan")
    if execution_plan is None:
        raise RoutingError("Execution plan is missing.")

    if set(execution_plan.workers) & PRICING_WORKERS:
        return "currency_node"

    return "response_generator"
