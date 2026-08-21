"""Service layer for the AI Travel Planner chat workflow."""

from langchain_core.messages import HumanMessage
from langgraph.types import Command

from Backend.Graph.builder import graph
from Backend.Logger import log_execution
from Backend.Schemas.api_schema import (
    ChatRequest,
    ChatResponse,
)


class TravelService:
    """Execute and resume the travel planning workflow."""

    @log_execution("TravelService")
    async def chat(
        self,
        request: ChatRequest,
    ) -> ChatResponse:
        """
        Start a new workflow or resume an interrupted workflow
        using the same thread_id.
        """

        config = {
            "configurable": {
                "thread_id": request.thread_id,
            }
        }

        # ==================================================
        # Check current checkpoint
        # ==================================================

        snapshot = await graph.aget_state(
            config,
        )

        has_interrupt = any(
            task.interrupts
            for task in snapshot.tasks
        )

        # ==================================================
        # Resume interrupted workflow
        # ==================================================

        if has_interrupt:

            result = await graph.ainvoke(
                Command(
                    resume=request.message,
                ),
                config=config,
            )

        # ==================================================
        # Start new workflow
        # ==================================================

        else:

            result = await graph.ainvoke(
                {
                    "messages": [
                        HumanMessage(
                            content=request.message,
                        )
                    ],

                    "clarification_required": False,

                    "clarification_questions": [],

                    "travel_plan": None,

                    "user_preferences": None,

                    "memory_context": None,

                    "execution_plan": None,

                    "flight_recommendations": None,

                    "hotel_recommendations": None,

                    "activity_recommendations": None,

                    "weather": None,

                    "currency": None,

                    "travel_packages": None,

                    "final_response": None,
                },
                config=config,
            )

        # ==================================================
        # Check for new interrupt
        # ==================================================

        interrupts = result.get(
            "__interrupt__",
            [],
        )

        if interrupts:

            interrupt_value = interrupts[0].value

            questions = interrupt_value.get(
                "questions",
                [],
            )

            # --------------------------------------------------
            # Normalize to list[str]
            # --------------------------------------------------

            if isinstance(
                questions,
                str,
            ):
                questions = [questions]

            questions = [
                str(question).strip()
                for question in questions
                if question
                and str(question).strip()
            ]

            # --------------------------------------------------
            # Safety fallback for old payloads
            # --------------------------------------------------

            if not questions:

                question = interrupt_value.get(
                    "question",
                )

                if isinstance(
                    question,
                    str,
                ):
                    questions = [question]

                elif isinstance(
                    question,
                    list,
                ):
                    questions = [
                        str(item).strip()
                        for item in question
                        if item
                        and str(item).strip()
                    ]

            # --------------------------------------------------
            # Convert questions to API response string
            # --------------------------------------------------

            if questions:

                response_text = "\n".join(
                    f"{index}. {question}"
                    for index, question in enumerate(
                        questions,
                        start=1,
                    )
                )

            else:

                response_text = (
                    "I need some more information."
                )

            return ChatResponse(
                thread_id=request.thread_id,
                response=response_text,
                interrupted=True,
            )

        # ==================================================
        # Completed workflow
        # ==================================================

        response = result.get(
            "final_response",
        )

        return ChatResponse(
            thread_id=request.thread_id,
            response=(
                response
                or "Trip planning completed."
            ),
            interrupted=False,
        )


service = TravelService()