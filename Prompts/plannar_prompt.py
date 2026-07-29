"""Planner prompt."""

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from Prompts.utils.prompt_loader import load_prompt

planner_prompt = ChatPromptTemplate.from_messages(
    [
        # System instructions
        ("system", load_prompt("planner.md")),

        # Current Travel Plan (from state/checkpoint)
        (
            "system",
            "Current Travel Plan:\n{existing_travel_plan}",
        ),

        # User Preferences (from memory, empty for now)
        (
            "system",
            "User Preferences:\n{user_preferences}",
        ),

        # Conversation
        MessagesPlaceholder(variable_name="messages"),
    ]
)