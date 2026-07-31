"""Orchestrator prompt."""

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from Prompts.utils.prompt_loader import load_prompt


travel_request_analyzer_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            load_prompt("travel_requester.md"),
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