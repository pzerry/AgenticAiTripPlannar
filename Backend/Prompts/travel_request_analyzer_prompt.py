from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from Backend.Prompts.utils.prompt_loader import load_prompt


travel_request_analyzer_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            load_prompt("travel_request_analyzer.md"),
        ),
        (
            "system",
            "Existing Travel Plan:\n{travel_plan}",
        ),
        MessagesPlaceholder(
            variable_name="messages"
        ),
        (
            "system",
            (
                "Today: {today}\n"
                "Current datetime: {current_datetime}\n"
                "Timezone: {timezone}"
            ),
        ),
    ]
)