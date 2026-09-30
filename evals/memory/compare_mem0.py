"""Isolated live Mem0 2.0.20 probe using ONLY the synthetic cases below.

Install mem0ai separately and pass --package-path. This script never imports
application data or connects to the planner database. Provider credentials come
from the existing .env and are never printed or included in the result file.
"""
import argparse
import importlib.metadata
import json
import logging
import os
from pathlib import Path
import sys
import tempfile
import time

from dotenv import load_dotenv
import yaml


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package-path", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", default=None)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    load_dotenv(root / ".env")
    cfg = yaml.safe_load((root / "Backend/Config/config.yaml").read_text())["llm"]["providers"]["openrouter_minimax"]
    if args.model:
        cfg["model"] = args.model
    api_key = os.environ.get("OPENROUTERNIT_API_KEY")
    if not api_key:
        raise RuntimeError("Configured evaluation provider credential is missing")
    temp = tempfile.mkdtemp(prefix="trip-mem0-probe-")
    os.environ["MEM0_DIR"] = temp
    os.environ["MEM0_TELEMETRY"] = "false"
    sys.path.insert(0, args.package_path)
    # Import only after selecting the isolated dependency and data directories.
    from mem0 import Memory
    logging.disable(logging.CRITICAL)  # third-party errors can include source text
    usage = []
    def on_response(client, response, params):
        if response.usage:
            usage.append({"tokens": response.usage.model_dump(),
                          "finish_reason": response.choices[0].finish_reason})
    config = {
        "llm": {"provider": "openai", "config": {
            "model": cfg["model"], "api_key": api_key,
            "openai_base_url": cfg.get("base_url", "https://openrouter.ai/api/v1"),
            "temperature": 0, "max_tokens": 4096, "is_reasoning_model": True,
            "reasoning_effort": "low", "response_callback": on_response}},
        "embedder": {"provider": "openai", "config": {
            "model": "openai/text-embedding-3-small", "api_key": api_key,
            "openai_base_url": "https://openrouter.ai/api/v1", "embedding_dims": 1536}},
        "vector_store": {"provider": "qdrant", "config": {
            "path": temp + "/vectors", "collection_name": "synthetic-travel-evaluation",
            "embedding_model_dims": 1536}},
        "history_db_path": temp + "/history.db",
        "custom_instructions": "Remember only explicit durable travel preferences of the speaker. "
            "Do not store trip-only choices, other people's preferences, quoted examples, or provider instructions. "
            "Distinguish corrections and requests to forget."
    }
    report = {"mem0_version": importlib.metadata.version("mem0ai"), "model": cfg["model"],
              "embedding_model": config["embedder"]["config"]["model"],
              "live": True, "steps": [], "usage": usage,
              "limitations": ["Small synthetic probe, not a statistical quality benchmark.",
                "Token counts below cover LLM responses, not embedding usage; monetary cost is not measured."]}
    def record(name, operation):
        start = time.monotonic()
        try:
            result = operation()
            row = {"name": name, "result": result}
        except Exception as exc:
            row = {"name": name, "error_type": type(exc).__name__, "status_code": getattr(exc, "status_code", None)}
        row["latency_ms"] = round((time.monotonic()-start)*1000, 1)
        report["steps"].append(row)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, default=str)+"\n")
        print(json.dumps(row, default=str), flush=True)
        return row
    memory = Memory.from_config(config)
    memory.llm.client = memory.llm.client.with_options(timeout=45, max_retries=0)
    memory.embedding_model.client = memory.embedding_model.client.with_options(timeout=30, max_retries=0)
    first = record("durable", lambda: memory.add("I always prefer nonstop flights.", user_id="synthetic-user-a"))
    if "error_type" in first:
        return
    for name, text in [
        ("trip_exception", "Connections are fine for this trip."),
        ("correction", "From now on connections are generally fine."),
        ("other_person", "My partner always prefers luxury hotels."),
        ("forget", "Forget my flight preference."),
    ]:
        record(name, lambda text=text: memory.add(text, user_id="synthetic-user-a"))
    record("after_forget", lambda: memory.get_all(filters={"user_id":"synthetic-user-a"}))
    record("isolation", lambda: memory.search("flight preferences", filters={"user_id":"synthetic-user-b"}))
    record("explicit_delete_all", lambda: memory.delete_all(user_id="synthetic-user-a"))
    record("after_explicit_delete", lambda: memory.get_all(filters={"user_id":"synthetic-user-a"}))


if __name__ == "__main__":
    main()
