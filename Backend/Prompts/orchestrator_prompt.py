"""Orchestrator prompt."""

from langchain_core.prompts import (
    ChatPromptTemplate,
    MessagesPlaceholder,
)

from Backend.Prompts.utils.prompt_loader import load_prompt


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
        MessagesPlaceholder(
            variable_name="messages"
        ),
    ]
)