"""Checkpoint conversation turns and isolate the replayable interrupt node."""

from uuid import UUID

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.types import interrupt
from pydantic import BaseModel, ConfigDict, Field

from Backend.Graph.state import TravelAgentState


class ClarificationAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message_id: UUID
    text: str = Field(min_length=1, max_length=32000, pattern=r"\S")
    memory_context: dict[str, str]
    memory_selected_ids: list[str]


def response_update(state: TravelAgentState, text: str) -> dict:
    message_id = state["current_message_id"]
    return {
        "response_message_id": message_id,
        "last_response": text,
        "messages": [AIMessage(content=text, id=f"response:{message_id}")],
    }


def clarification(state: TravelAgentState) -> dict:
    # No side effects before interrupt: LangGraph replays this node on resume.
    # The API captured the answer before constructing this payload.
    answer = ClarificationAnswer.model_validate(interrupt({
        "type": "clarification", "questions": state["clarification_questions"]
    }))
    return {
        "messages": [HumanMessage(content=answer.text, id=str(answer.message_id))],
        "current_message_id": str(answer.message_id),
        "memory_context": answer.memory_context,
        "memory_selected_ids": answer.memory_selected_ids,
        "clarification_required": False,
        "clarification_questions": [],
        "final_response": None,
    }


def record_response(state: TravelAgentState) -> dict:
    text = state.get("final_response")
    if not isinstance(text, str) or not text.strip():
        raise ValueError("The planner did not produce a text response")
    return response_update(state, text)
