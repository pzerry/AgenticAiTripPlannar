"""Orchestrator prompt."""

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from Prompts.utils.prompt_loader import load_prompt


orchestrator_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            load_prompt("orchestrator.md"),
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