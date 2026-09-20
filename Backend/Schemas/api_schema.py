from pydantic import BaseModel, Field
from uuid import UUID,uuid4


class ChatRequest(BaseModel):
    """Incoming chat request."""

    # Identity comes from the verified bearer token. The optional legacy field
    # is checked for equality; it never grants access to another user's data.
    user_id: UUID | None = None
    message_id: UUID = Field(description="Generate once per message and reuse on every retry.")
    thread_id: str = Field(default_factory=lambda: str(uuid4()), min_length=1, max_length=256, pattern=r"\S")
    message: str = Field(min_length=1, max_length=32000, pattern=r"\S")


class ChatResponse(BaseModel):
    """Response returned by the travel planning workflow."""

    thread_id: str
    message_id: UUID
    response: str
    memory_status: str = Field(description="Extraction status at response time; processing is asynchronous.")
    interrupted: bool = Field(default=False, description="Whether the workflow is waiting for user clarification.")
