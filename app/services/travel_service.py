"""Authenticated chat orchestration: capture, retrieve, run/resume, then receipt."""

from uuid import UUID

from langchain_core.messages import HumanMessage
from langgraph.types import Command

from Backend.Logger import log_execution
from Backend.Memory.chat_turns import begin_turn, event_status, finish_turn, thread_guard
from Backend.Memory.events import EventRepository, MessageInput, OwnershipError
from Backend.Schemas.api_schema import ChatRequest, ChatResponse
from app.auth import Principal


class LegacyInterruptError(ValueError):
    """The old analyzer stored clarification inside a now-replaced node."""


class TravelService:
    def __init__(self, graph, memory_pool) -> None:
        self.graph = graph
        self.memory_pool = memory_pool

    @log_execution("TravelService")
    async def chat(self, request: ChatRequest, principal: Principal) -> ChatResponse:
        if request.user_id is not None and request.user_id != principal.user_id:
            raise OwnershipError("Request identity does not match the signed-in user")
        message = MessageInput(user_id=principal.user_id, message_id=request.message_id,
                               thread_id=request.thread_id, text=request.message)
        config = {"configurable": {"thread_id": request.thread_id}}

        async with thread_guard(self.memory_pool, user_id=principal.user_id,
                                thread_id=request.thread_id) as conn:
            snapshot = await self.graph.aget_state(config)
            self._check_checkpoint_owner(snapshot, principal)
            if any(task.interrupts and task.name != "clarification" for task in snapshot.tasks):
                raise LegacyInterruptError("This conversation uses the old clarification flow; start a new chat")

            memory, selected_ids, cached = await begin_turn(conn, message)
            if cached is None:
                await self._advance(request, principal, snapshot, config, memory, selected_ids)
                # Read the durable result, not only ainvoke's return value. If
                # the API dies before finish_turn, retry can recover this state.
                snapshot = await self.graph.aget_state(config)
                interrupted = any(task.interrupts for task in snapshot.tasks)
                values = snapshot.values
                if (values.get("response_message_id") != str(request.message_id)
                        or (snapshot.next and not interrupted)):
                    raise RuntimeError("The graph has not checkpointed a complete turn response")
                cached = {
                    "thread_id": request.thread_id,
                    "message_id": str(request.message_id),
                    "response": values["last_response"],
                    "interrupted": interrupted,
                }
                await finish_turn(conn, message, cached)

            status = await event_status(conn, user_id=principal.user_id, message_id=request.message_id)
            return ChatResponse(**cached, memory_status=status)

    async def _advance(self, request, principal, snapshot, config, memory, selected_ids):
        """Distinguish an HTTP retry from a new answer to an interrupt."""
        values = snapshot.values
        same_message = values.get("current_message_id") == str(request.message_id)
        interrupted = any(task.interrupts for task in snapshot.tasks)
        if same_message:
            if (values.get("response_message_id") == str(request.message_id)
                    and (interrupted or not snapshot.next)):
                return  # Graph finished; only the HTTP receipt was lost.
            if snapshot.next and not interrupted:
                await self.graph.ainvoke(None, config=config)  # Resume failed node.
                return
            raise RuntimeError("Cannot recover the unfinished graph turn")

        if interrupted:
            # All fields here are assembled by this authenticated service.
            # The clarification node saves the answer with its stable message ID.
            await self.graph.ainvoke(Command(resume={
                "message_id": str(request.message_id),
                "text": request.message,
                "memory_context": memory,
                "memory_selected_ids": selected_ids,
            }), config=config)
            return

        if snapshot.next:
            # A legacy or externally modified checkpoint has pending work that
            # cannot safely be attributed to this new message.
            raise LegacyInterruptError("Conversation has unfinished legacy work; start a new chat")
        await self.graph.ainvoke({
            "user_id": principal.user_id,
            "messages": [HumanMessage(content=request.message, id=str(request.message_id))],
            "current_message_id": str(request.message_id),
            "memory_context": memory,
            "memory_selected_ids": selected_ids,
            "clarification_required": False,
            "clarification_questions": [],
            "final_response": None,
        }, config=config)

    @staticmethod
    def _check_checkpoint_owner(snapshot, principal):
        if not snapshot.values:
            return
        try:
            owner = UUID(str(snapshot.values.get("user_id")))
        except (ValueError, TypeError):
            raise OwnershipError("Checkpoint ownership cannot be verified") from None
        if owner != principal.user_id:
            raise OwnershipError("Thread is not owned by this user")

    async def debug_state(self, thread_id: str, principal: Principal) -> dict:
        """Do not expose checkpoint contents before verifying thread ownership."""
        async with thread_guard(self.memory_pool, user_id=principal.user_id, thread_id=thread_id) as conn:
            await EventRepository().assert_owner(conn, user_id=principal.user_id, thread_id=thread_id)
            snapshot = await self.graph.aget_state({"configurable": {"thread_id": thread_id}})
            self._check_checkpoint_owner(snapshot, principal)
            return {"thread_id": thread_id, "values": snapshot.values,
                    "has_interrupt": any(task.interrupts for task in snapshot.tasks)}
