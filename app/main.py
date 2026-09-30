from contextlib import asynccontextmanager

from fastapi import FastAPI
from psycopg_pool import AsyncConnectionPool

from Backend.Config.env import env
from Backend.Graph.builder import create_travel_graph
from Backend.Memory.migrate import require_migrations
from Backend.Logger import setup_logging
from Backend.Logger.middleware import LoggingMiddleware
from app.api.router import router
from app.exception_handlers import register_exception_handlers
from app.services.travel_service import TravelService


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown."""

    # The memory pool is separate from the graph checkpoint pool. A chat holds
    # a session lock while planning; checkpoints still need free DB connections.
    async with AsyncConnectionPool(env.DATABASE_URL, min_size=1, max_size=10,
                                   kwargs={"autocommit": True}) as memory_pool:
        async with memory_pool.connection() as conn:
            await require_migrations(conn)
        async with create_travel_graph() as (graph, checkpointer):
            app.state.travel_graph = graph
            app.state.travel_service = TravelService(graph, memory_pool)
            yield


setup_logging()

app = FastAPI(
    title="Agentic AI Trip Planner",
    description="Multi-agent AI Travel Planner with persistent conversation and preference memory",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/")
async def root():
    return {"message": "AI Travel Planner API is running."}


app.add_middleware(LoggingMiddleware)

register_exception_handlers(app)

app.include_router(router)
