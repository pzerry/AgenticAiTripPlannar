"""Build the same workflow for the API and deterministic integration tests."""

from contextlib import asynccontextmanager
from importlib import import_module
from typing import AsyncIterator

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import END, START, StateGraph
from psycopg_pool import AsyncConnectionPool

from Backend.Graph.checkpoint import checkpoint_serializer
from Backend.Graph.nodes.conversation import clarification, record_response
from Backend.Graph.nodes.router import analyzer_router, fanout, worker_router
from Backend.Graph.nodes.travel_requester import travel_request_analyzer
from Backend.Graph.state import TravelAgentState


def build_travel_graph(*, node_overrides: dict | None = None) -> StateGraph:
    """Overrides replace external model/tool calls, never the graph's edges."""
    overrides = dict(node_overrides or {})
    builder = StateGraph(TravelAgentState)
    nodes = {
        "travel_request_analyzer": travel_request_analyzer,
        "clarification": clarification,
        "record_response": record_response,
    }
    external_nodes = {
        "orchestrator": ("Backend.Graph.nodes.orchestrator", "orchestrator"),
        "flight_agent": ("Backend.Graph.agents.flight_agent", "flight_agent"),
        "hotel_agent": ("Backend.Graph.agents.hotel_agent", "hotel_agent"),
        "activity_agent": ("Backend.Graph.agents.activity_agent", "activity_agent"),
        "weather_node": ("Backend.Graph.nodes.weatherNode", "weather_node"),
        "currency_node": ("Backend.Graph.nodes.currencyNode", "currency_node"),
        "response_generator": ("Backend.Graph.nodes.response_generator", "response_generator"),
    }
    if set(overrides) - (nodes.keys() | external_nodes.keys()):
        raise ValueError("Unknown graph node override")
    for name, (module, function) in external_nodes.items():
        # Lazy imports let tests use this workflow without constructing real
        # provider clients or requiring API keys.
        nodes[name] = overrides[name] if name in overrides else getattr(import_module(module), function)
    nodes.update(overrides)
    for name, node in nodes.items():
        builder.add_node(name, node, defer=name == "currency_node")

    builder.add_edge(START, "travel_request_analyzer")
    builder.add_conditional_edges("travel_request_analyzer", analyzer_router)
    builder.add_edge("clarification", "travel_request_analyzer")
    builder.add_conditional_edges("orchestrator", fanout)
    for name in ("flight_agent", "hotel_agent", "activity_agent", "weather_node"):
        builder.add_conditional_edges(name, worker_router)
    builder.add_edge("currency_node", "response_generator")
    builder.add_edge("response_generator", "record_response")
    builder.add_edge("record_response", END)
    return builder


@asynccontextmanager
async def create_travel_graph() -> AsyncIterator:
    """Keep the checkpoint pool alive for the application's lifetime."""
    from Backend.Config.env import env

    if not env.DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not configured.")
    async with AsyncConnectionPool(
        conninfo=env.DATABASE_URL, min_size=1, max_size=10,
        kwargs={"autocommit": True},
    ) as pool:
        checkpointer = AsyncPostgresSaver(pool, serde=checkpoint_serializer())
        await checkpointer.setup()
        graph = build_travel_graph().compile(checkpointer=checkpointer)
        yield graph, checkpointer
