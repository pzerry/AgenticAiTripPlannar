from fastapi import APIRouter, status

router = APIRouter(
    prefix="/health",
    tags=["Health"],
)


@router.get(
    "",
    status_code=status.HTTP_200_OK,
)
async def health_check() -> dict:
    """Health check endpoint."""

    return {
        "status": "healthy",
    }