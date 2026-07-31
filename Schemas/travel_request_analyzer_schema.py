"""Schemas for the Travel Request Analyzer node."""

from pydantic import BaseModel, Field

from Schemas.travel_schema import TravelPlan


class TravelRequestAnalyzerOutput(BaseModel):
    """
    Output produced by the Travel Request Analyzer.

    Responsibilities:
    - Extract structured travel information from the conversation.
    - Update the current TravelPlan.
    - Identify whether clarification is required.

    It does NOT decide which workers should execute.
    """

    travel_plan: TravelPlan = Field(
        description="The updated structured travel plan extracted from the conversation."
    )

    clarification_required: bool = Field(
        default=False,
        description="Whether additional user information is required."
    )

    clarification_question: str | None = Field(
        default=None,
        description="Question to ask the user when required information is missing."
    )