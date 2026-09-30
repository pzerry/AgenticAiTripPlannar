"""Exercise production orchestration with Groq's HTTP boundary mocked."""

import json
import unittest
from unittest.mock import patch

import httpx
from langchain_core.messages import HumanMessage
from langchain_groq import ChatGroq

from Backend.Exceptions.exception import GraphStateError
from Backend.Graph.nodes.orchestrator import get_orchestrator_chain, orchestrator
from Backend.Schemas.orchestrator_schema import ExecutionPlan, TravelIntent, WorkerType
from Backend.Schemas.travel_schema import TravelPlan


class OrchestratorJsonModeTests(unittest.IsolatedAsyncioTestCase):
    async def invoke(self, content):
        self.sent = []

        def endpoint(request):
            self.sent.append(json.loads(request.content))
            return httpx.Response(200, json={
                "id": "test-completion", "object": "chat.completion", "created": 0,
                "model": "test-model", "choices": [{"index": 0, "finish_reason": "stop",
                    "message": {"role": "assistant", "content": content}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20},
            })

        get_orchestrator_chain.cache_clear()
        self.addCleanup(get_orchestrator_chain.cache_clear)
        async with httpx.AsyncClient(transport=httpx.MockTransport(endpoint)) as client:
            llm = ChatGroq(model="test-model", api_key="test-key", max_retries=0,
                           http_async_client=client)
            # Keep production chain construction, prompts and parsing intact.
            with patch("Backend.LLM.factory.get_llm", return_value=llm):
                return await orchestrator({
                    "travel_plan": TravelPlan(destination="Paris"),
                    "messages": [HumanMessage(content="Plan a trip to Paris")],
                }, {})

    async def test_fenced_response_from_report_is_validated(self):
        content = '```json\n{"intent":"full_plan","workers":["FLIGHT","HOTEL","ACTIVITY","WEATHER"]}\n```'
        result = await self.invoke(content)
        plan = result["execution_plan"]
        self.assertIsInstance(plan, ExecutionPlan)
        self.assertEqual(plan.intent, TravelIntent.FULL_PLAN)
        self.assertEqual(plan.workers, [WorkerType.FLIGHT, WorkerType.HOTEL, WorkerType.ACTIVITY, WorkerType.WEATHER])
        self.assertEqual(self.sent[0]["response_format"], {"type": "json_object"})
        instruction = next(message["content"] for message in self.sent[0]["messages"]
                           if message["role"] == "system" and "JSON schema:\n" in message["content"])
        schema = json.loads(instruction.split("JSON schema:\n", 1)[1])
        self.assertEqual(set(schema["required"]), {"intent", "workers"})

    async def test_plain_json_response_is_validated(self):
        result = await self.invoke('{"intent":"weather_only","workers":["WEATHER"]}')
        self.assertEqual(result["execution_plan"].workers, [WorkerType.WEATHER])

    async def test_invalid_outputs_do_not_dispatch_or_expose_raw_response(self):
        for content in (
            "private-test-response: unable to make a plan",
            '{"intent":"weather_only","workers":[]}',
            '{"intent":"weather_only","workers":["UNKNOWN_WORKER"]}',
            '{"intent":"unknown_intent","workers":["WEATHER"]}',
            "",
        ):
            with self.subTest(content=content):
                with self.assertLogs("trip_planner.Backend.Logger.events", level="ERROR") as logs:
                    with self.assertRaisesRegex(GraphStateError, "invalid execution plan"):
                        await self.invoke(content)
                self.assertNotIn("private-test-response", "\n".join(logs.output))
                self.assertNotIn("UNKNOWN_WORKER", "\n".join(logs.output))
