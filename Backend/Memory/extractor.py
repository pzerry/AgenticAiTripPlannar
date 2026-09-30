"""Replaceable extraction boundary used by the worker and evaluation harness."""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Protocol

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, ConfigDict, Field

from Backend.Memory.contracts import EvidenceSpan, MemoryCandidate, MessageContext
from Backend.Memory.models import ALLOWED_VALUES, MemoryKey


class ProposedPreference(BaseModel):
    model_config = ConfigDict(extra="forbid")
    operation: Literal["upsert", "delete"]
    memory_key: MemoryKey
    memory_value: str | None
    subject: Literal["self", "other", "unknown"]
    scope: Literal["durable", "trip", "unknown"]
    assertion: Literal["explicit", "inferred", "unknown"]
    quote: str = Field(min_length=1, max_length=2000)


class ExtractionOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    candidates: list[ProposedPreference] = Field(default_factory=list, max_length=3)


@dataclass(frozen=True)
class ExtractionResult:
    candidates: list[MemoryCandidate]
    usage: dict[str, int] = field(default_factory=dict)


class Extractor(Protocol):
    async def extract(self, context: MessageContext) -> ExtractionResult: ...


def validate_proposals(text: str, output: ExtractionOutput) -> list[MemoryCandidate]:
    """Derive evidence offsets in code. Reject missing or ambiguous quotations."""
    output = ExtractionOutput.model_validate(output.model_dump())
    if len({p.memory_key for p in output.candidates}) != len(output.candidates):
        raise ValueError("Extractor proposed conflicting candidates for the same key")
    candidates = []
    for proposal in output.candidates:
        start = text.find(proposal.quote)
        if start < 0 or text.find(proposal.quote, start + 1) >= 0:
            raise ValueError("Evidence must identify exactly one source span")
        candidates.append(MemoryCandidate(
            **proposal.model_dump(exclude={"quote"}),
            evidence=EvidenceSpan(start=start, end=start + len(proposal.quote), quote=proposal.quote)))
    return candidates


class StructuredExtractor:
    """LLM implementation for controlled comparison; contains no persistence."""

    def __init__(self, llm, *, method: Literal["json_schema", "json_mode"] = "json_mode"):
        self.chain = llm.with_structured_output(ExtractionOutput, method=method, include_raw=True)
        self.method = method
        self.prompt = (Path(__file__).parent / "prompts" / "extract_preferences.md").read_text()
        if method == "json_mode":
            self.prompt += "\nReturn JSON matching this schema:\n" + json.dumps(ExtractionOutput.model_json_schema())

    async def extract(self, context: MessageContext) -> ExtractionResult:
        context = MessageContext.model_validate(context.model_dump())
        if context.role != "user":
            return ExtractionResult([])
        response = await self.chain.ainvoke([
            SystemMessage(content=self.prompt + "\nSupported values:\n" + json.dumps(
                {key: sorted(values) for key, values in ALLOWED_VALUES.items()})),
            HumanMessage(content=json.dumps({"source_message": context.text}, ensure_ascii=False)),
        ])
        metadata = getattr(response.get("raw"), "response_metadata", None) or {}
        if metadata.get("finish_reason") == "length":
            raise ValueError("Extractor response was truncated")
        if response.get("parsing_error") or response.get("parsed") is None:
            raise ValueError("Extractor returned invalid structured output")
        output = ExtractionOutput.model_validate(response["parsed"])
        raw_usage = getattr(response.get("raw"), "usage_metadata", None) or {}
        usage = {key: value for key, value in raw_usage.items()
                 if key in {"input_tokens", "output_tokens", "total_tokens"} and isinstance(value, int)}
        return ExtractionResult(validate_proposals(context.text, output), usage)
