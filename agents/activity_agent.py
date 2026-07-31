"""Activity Agent."""

from pathlib import Path

from langgraph.prebuilt import create_react_agent

from llm import llm
from tools.activity_tool import search_activities

PROMPT_PATH = (
    Path(__file__).parent / "prompts" / "activity_agent_prompt.md"
)

SYSTEM_PROMPT = PROMPT_PATH.read_text(encoding="utf-8")


activity_agent = create_react_agent(
    model=llm,
    tools=[search_activities],
    prompt=SYSTEM_PROMPT,
)