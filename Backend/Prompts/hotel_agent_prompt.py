"""Orchestrator prompt."""

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from Backend.Prompts.utils.prompt_loader import load_prompt


hotel_agent_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            load_prompt("hotel_agent.md"),
        ),
        (
            "system",
            "Existing Travel Plan:\n{travel_plan}",
        ),
        (
            "system",
            "User Preferences:\n{user_preferences}",
        ),
        MessagesPlaceholder(variable_name="messages"),
    ]
)