"""LangGraph workflow definition for the AI Travel Planner."""

from typing import Literal

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from Backend.Graph.agents.activity_agent import activity_agent
from Backend.Graph.agents.flight_agent import flight_agent
from Backend.Graph.agents.hotel_agent import hotel_agent
from Backend.Graph.nodes.currencyNode import currency_node
from Backend.Graph.nodes.orchestrator import orchestrator
from Backend.Graph.nodes.packet_generator import package_agent
from Backend.Graph.nodes.response_generator import response_generator
from Backend.Graph.nodes.router import analyzer_router, fanout
from Backend.Graph.nodes.travel_requester import travel_request_analyzer
from Backend.Graph.nodes.weatherNode import weather_node
from Backend.Graph.state import TravelAgentState


# ==========================================================
# Checkpointer
# ==========================================================

checkpointer = MemorySaver()


# ==========================================================
# Graph
# ==========================================================

builder = StateGraph(TravelAgentState)


# ==========================================================
# Nodes
# ==========================================================

builder.add_node(
    "travel_request_analyzer",
    travel_request_analyzer,
)

builder.add_node(
    "orchestrator",
    orchestrator,
)

builder.add_node(
    "flight_agent",
    flight_agent,
)

builder.add_node(
    "hotel_agent",
    hotel_agent,
)

builder.add_node(
    "activity_agent",
    activity_agent,
)

builder.add_node(
    "weather_node",
    weather_node,
)

builder.add_node(
    "currency_node",
    currency_node,
)

builder.add_node(
    "package_agent",
    package_agent,
    defer=True,
)

builder.add_node(
    "response_generator",
    response_generator,
)


# ==========================================================
# Entry
# ==========================================================

builder.add_edge(
    START,
    "travel_request_analyzer",
)


# ==========================================================
# Analyzer → Orchestrator
# ==========================================================

builder.add_conditional_edges(
    "travel_request_analyzer",
    analyzer_router,
)


# ==========================================================
# Orchestrator → Workers
# ==========================================================

builder.add_conditional_edges(
    "orchestrator",
    fanout,
)


# ==========================================================
# Worker Router
# ==========================================================

def worker_router(
    state: TravelAgentState,
) -> Literal[
    "package_agent",
    "response_generator",
]:
    """
    Route worker results.

    Full plans:
        worker → package_agent

    Direct requests:
        worker → response_generator
    """

    execution_plan = state.get(
        "execution_plan"
    )

    if execution_plan is None:
        raise ValueError(
            "Execution plan is missing."
        )

    if execution_plan.intent.value == "full_plan":
        return "package_agent"

    return "response_generator"


# ==========================================================
# Workers → Next Step
# ==========================================================

for worker in [
    "flight_agent",
    "hotel_agent",
    "activity_agent",
    "weather_node",
]:
    builder.add_conditional_edges(
        worker,
        worker_router,
    )


# ==========================================================
# Full Plan Pipeline
#
# Package → Currency → Response → END
# ==========================================================

builder.add_edge(
    "package_agent",
    "currency_node",
)

builder.add_edge(
    "currency_node",
    "response_generator",
)


# ==========================================================
# Direct Request / Full Plan → END
# ==========================================================

builder.add_edge(
    "response_generator",
    END,
)


# ==========================================================
# Compile
# ==========================================================

graph = builder.compile(
    checkpointer=checkpointer,
)