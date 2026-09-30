"""Travel endpoints: verified identity is required before accessing any state."""

from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Response

from app.auth import Principal, get_current_user
from app.dependencies import get_travel_service
from Backend.Memory.chat_turns import event_status
from Backend.Memory.models import MemoryKey
from Backend.Memory.management import forget_preference
from Backend.Memory.semantic_memory import SemanticMemoryRepository
from Backend.Schemas.api_schema import ChatRequest, ChatResponse
from app.services.travel_service import TravelService

router = APIRouter()


@router.get("/travel/me")
async def current_user(principal: Principal = Depends(get_current_user)):
    return {"user_id": str(principal.user_id)}


@router.post("/travel/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    service: TravelService = Depends(get_travel_service),
    principal: Principal = Depends(get_current_user),
):
    return await service.chat(request, principal)


@router.get("/travel/debug/state/{thread_id}")
async def debug_state(
    thread_id: str,
    service: TravelService = Depends(get_travel_service),
    principal: Principal = Depends(get_current_user),
):
    return await service.debug_state(thread_id, principal)


@router.get("/travel/memories")
async def memories(
    service: TravelService = Depends(get_travel_service),
    principal: Principal = Depends(get_current_user),
):
    async with service.memory_pool.connection() as conn:
        rows = await SemanticMemoryRepository().get_all(conn, user_id=principal.user_id)
    return {"memories": [row.model_dump(mode="json") for row in rows]}


@router.get("/travel/memory-events/{message_id}")
async def memory_event(
    message_id: UUID,
    service: TravelService = Depends(get_travel_service),
    principal: Principal = Depends(get_current_user),
):
    async with service.memory_pool.connection() as conn:
        status = await event_status(conn, user_id=principal.user_id, message_id=message_id)
    if status is None:
        raise HTTPException(404, "Memory event not found")
    return {"message_id": str(message_id), "status": status}


@router.delete("/travel/memories/{memory_key}", status_code=204)
async def forget_memory(
    memory_key: MemoryKey,
    request_id: UUID = Header(alias="Idempotency-Key"),
    service: TravelService = Depends(get_travel_service),
    principal: Principal = Depends(get_current_user),
):
    async with service.memory_pool.connection() as conn:
        await forget_preference(conn, user_id=principal.user_id, memory_key=memory_key, request_id=request_id)
    return Response(status_code=204)
