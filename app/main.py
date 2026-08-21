from contextlib import asynccontextmanager

from fastapi import FastAPI

from Backend.Logger import setup_logging
from Backend.Logger.middleware import LoggingMiddleware
from app.api.router import router
from app.exception_handlers import register_exception_handlers

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown."""
    yield


setup_logging()

app = FastAPI(
    title="Agentic AI Trip Planner",
    description="Production-grade Multi-Agent AI Travel Planner",
    version="1.0.0",
    lifespan=lifespan,
)

@app.get("/")
async def root():
    return {
        "message": "AI Travel Planner API is running."
    }



app.add_middleware(LoggingMiddleware)

register_exception_handlers(app)

app.include_router(router)