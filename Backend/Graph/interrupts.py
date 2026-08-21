from langgraph.types import interrupt


def request_clarification(question: str):
    """
    Pause graph execution and wait for user input.
    """

    return interrupt(
        {
            "type": "clarification",
            "question": question,
        }
    )