"""Router node."""

from langgraph.constants import Send

from Graph.state import TravelAgentState


def fanout(state: TravelAgentState) -> list[Send]:
    """
    Fan out execution to the required worker nodes.

    Reads the ExecutionPlan produced by the Orchestrator and
    dispatches each task to its corresponding worker.

    Returns:
        List of Send objects for parallel execution.
    """

    execution_plan = state.get("execution_plan")

    if execution_plan is None:
        return []

    sends: list[Send] = []

    for task in execution_plan.tasks:
        sends.append(
            Send(
                f"{task.worker.value}_worker",
                {
                    "travel_plan": state["travel_plan"],
                    "task": task,
                },
            )
        )

    return sends