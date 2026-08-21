from pydantic import BaseModel, Field
from uuid import uuid4


class ChatRequest(BaseModel):
    """Incoming chat request."""

    thread_id: str = Field(default_factory=lambda: str(uuid4()), description="Conversation/checkpoint identifier.")
    message: str = Field(min_length=1, description="User's message.")


class ChatResponse(BaseModel):
    """Response returned by the travel planning workflow."""

    thread_id: str
    response: str
    interrupted: bool = Field(default=False, description="Whether the workflow is waiting for user clarification.")