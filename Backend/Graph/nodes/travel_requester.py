"""One checkpointed analysis step; clarification lives in a separate node."""

from datetime import datetime
from functools import lru_cache
import json
from zoneinfo import ZoneInfo

from langchain_core.runnables import RunnableConfig

from Backend.Graph.state import TravelAgentState
from Backend.Graph.nodes.conversation import response_update
from Backend.Logger.decorators import log_agent
from Backend.Memory.retrieval import merge_plan_with_memory
from Backend.Prompts.travel_request_analyzer_prompt import travel_request_analyzer_prompt
from Backend.Schemas.travel_request_analyzer_schema import TravelRequestAnalyzerOutput

TIMEZONE = "Asia/Kolkata"


@lru_cache(maxsize=1)
def get_analysis_chain():
    from Backend.LLM.factory import get_llm

    return travel_request_analyzer_prompt | get_llm("ollama_qwen3").with_structured_output(
        TravelRequestAnalyzerOutput, method="json_mode"
    )


async def analyze_request(state: TravelAgentState, config: RunnableConfig, *, chain) -> dict:
    """Inject the model boundary in tests while exercising the production merge."""
    now = datetime.now(ZoneInfo(TIMEZONE))
    memory = state.get("memory_context") or {}
    # Refresh defaults before showing the plan to the analyzer, so an erased
    # preference cannot be copied from stale checkpoint state.
    plan, defaults = merge_plan_with_memory(
        state.get("travel_plan"), {}, memory, state.get("memory_applied_defaults")
    )
    result = TravelRequestAnalyzerOutput.model_validate(await chain.ainvoke({
        "travel_plan": plan.model_dump(mode="json"),
        "messages": list(state.get("messages", [])),
        "memory_context": json.dumps(memory, sort_keys=True),
        "memory_applied_defaults": json.dumps(defaults, sort_keys=True),
        "today": now.strftime("%Y-%m-%d"),
        "current_datetime": now.isoformat(),
        "timezone": TIMEZONE,
    }, config=config))
    plan, defaults = merge_plan_with_memory(
        plan, result.updates.model_dump(exclude_none=True), memory, defaults
    )
    questions = [question.strip() for question in result.clarification_questions if question.strip()]
    if result.clarification_required and not questions:
        raise ValueError("Clarification requires at least one question")
    update = {
        "travel_plan": plan,
        "memory_applied_defaults": defaults,
        "currency_request": result.currency_request,
        "clarification_required": result.clarification_required,
        "clarification_questions": questions if result.clarification_required else [],
    }
    if result.clarification_required:
        text = "\n".join(f"{index}. {question}" for index, question in enumerate(questions, 1))
        update.update(response_update(state, text))
    return update


@log_agent("travel_request_analyzer")
async def travel_request_analyzer(state: TravelAgentState, config: RunnableConfig) -> dict:
    return await analyze_request(state, config, chain=get_analysis_chain())
