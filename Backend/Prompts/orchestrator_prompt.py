"""Orchestrator prompt."""

import json

from langchain_core.prompts import (
    ChatPromptTemplate,
    MessagesPlaceholder,
)

from Backend.Prompts.utils.prompt_loader import load_prompt
from Backend.Schemas.orchestrator_schema import ExecutionPlan


orchestrator_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            load_prompt("orchestrator.md"),
        ),
        (
            "system",
            # JSON mode constrains syntax, not the execution-plan fields.
            # Supply the schema in the prompt and validate the response too.
            "Return only a valid JSON object without Markdown fences or commentary, "
            "matching this JSON schema:\n{output_schema}",
        ),
        (
            "system",
            "Existing Travel Plan:\n{travel_plan}",
        ),
        MessagesPlaceholder(
            variable_name="messages"
        ),
    ]
).partial(output_schema=json.dumps(ExecutionPlan.model_json_schema()))
