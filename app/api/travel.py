from fastapi import APIRouter, Depends, status

from Backend.Schemas.api_schema import ChatRequest, ChatResponse
from app.dependencies import get_travel_service
from app.services.travel_service import TravelService

router = APIRouter(
    prefix="/travel",
    tags=["Travel"],
)


@router.post(
    "/chat",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
)
async def chat(
    request: ChatRequest,
    service: TravelService = Depends(get_travel_service),
) -> ChatResponse:

    return await service.chat(request)