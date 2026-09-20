"""Live synthetic extraction evaluation. Never loads user conversations."""
import argparse
import asyncio
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import time
from uuid import uuid4

from Backend.Memory.contracts import MessageContext
from Backend.Memory.extractor import StructuredExtractor
from Backend.Memory.policy import evaluate_candidate

ROOT = Path(__file__).resolve().parents[2]


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider", default="openrouter_minimax")
    parser.add_argument("--model", default=None, help="Explicit evaluation-only model override")
    parser.add_argument("--method", choices=["json_schema", "json_mode"], default="json_mode")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()
    from Backend.LLM.factory import get_llm
    llm = get_llm(args.provider).model_copy(update={"max_tokens": 4096, "max_retries": 0, "timeout": 45})
    if args.model:
        llm = llm.model_copy(update={"model_name": args.model})
    extractor = StructuredExtractor(llm, method=args.method)
    cases_path = ROOT / "evals" / "memory" / "cases.json"
    cases = json.loads(cases_path.read_text())
    if args.limit:
        cases = cases[:args.limit]
    report = {"run_at": datetime.now(timezone.utc).isoformat(), "provider": args.provider,
              "model": getattr(llm, "model_name", None), "live": True,
              "output_method": args.method,
              "dataset_sha256": hashlib.sha256(cases_path.read_bytes()).hexdigest(),
              "prompt_sha256": hashlib.sha256(extractor.prompt.encode()).hexdigest(),
              "langchain_core": importlib.metadata.version("langchain-core"), "cases": []}
    for case in cases:
        started = time.monotonic()
        row = {"id": case["id"], "expected": case["expected"]}
        try:
            async with asyncio.timeout(50):
                result = await extractor.extract(MessageContext(user_id=uuid4(), message_id=uuid4(),
                    thread_id="synthetic-eval", sequence=1, occurred_at=datetime.now(timezone.utc),
                    role="user", text=case["text"]))
            context = MessageContext(user_id=uuid4(), message_id=uuid4(), thread_id="synthetic-eval",
                sequence=1, occurred_at=datetime.now(timezone.utc), role="user", text=case["text"])
            actual = [[c.operation, c.memory_key, c.memory_value] for c in result.candidates
                      if evaluate_candidate(context, c).eligible]
            row.update(actual=actual, passed=sorted(actual)==sorted(case["expected"]), usage=result.usage)
        except Exception as exc:
            row.update(passed=False, error_type=type(exc).__name__, status_code=getattr(exc, "status_code", None))
        row["latency_ms"] = round((time.monotonic() - started)*1000, 1)
        report["cases"].append(row)
        print(json.dumps(row), flush=True)
        # Preserve completed evidence after each call; no credentials or exception bodies.
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n")
    report["passed"] = sum(row["passed"] for row in report["cases"])
    report["total"] = len(cases)
    report["release_gate_passed"] = report["passed"] == len(cases) and len(cases) == 15
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    if report["passed"] != len(cases):
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
