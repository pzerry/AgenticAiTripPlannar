"""Check the actual Groq request contract without sending data to a provider."""

import json
import unittest

import httpx
from langchain_core.messages import HumanMessage
from langchain_groq import ChatGroq

from Backend.Graph.nodes.travel_requester import analyze_request
from Backend.Prompts.travel_request_analyzer_prompt import travel_request_analyzer_prompt
from Backend.Schemas.travel_request_analyzer_schema import TravelRequestAnalyzerOutput


class AnalyzerJsonModeTests(unittest.IsolatedAsyncioTestCase):
    async def test_plain_user_message_sends_json_instructions_and_parses_output(self):
        requests = []

        def groq_endpoint(request):
            payload = json.loads(request.content)
            requests.append(payload)
            # Reproduce Groq's validation at the HTTP boundary. Mocking the
            # analyzer result directly would miss this request-format failure.
            if not any("json" in message["content"].lower() for message in payload["messages"]):
                return httpx.Response(400, json={"error": {
                    "message": "'messages' must contain the word 'json' in some form",
                    "type": "invalid_request_error",
                }})
            return httpx.Response(200, json={
                "id": "test-completion", "object": "chat.completion", "created": 0,
                "model": "test-model", "choices": [{"index": 0, "finish_reason": "stop",
                    "message": {"role": "assistant", "content": json.dumps({
                        "updates": {"destination": "Paris"}, "clarification_required": True,
                        "clarification_questions": ["When would you like to travel?"],
                        "currency_request": None,
                    })}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20},
            })

        async with httpx.AsyncClient(transport=httpx.MockTransport(groq_endpoint)) as client:
            llm = ChatGroq(model="test-model", api_key="test-key", max_retries=0,
                           http_async_client=client)
            chain = travel_request_analyzer_prompt | llm.with_structured_output(
                TravelRequestAnalyzerOutput, method="json_mode")
            result = await analyze_request({
                "messages": [HumanMessage(content="Plan a trip to Paris")],
                "current_message_id": "test-message",
                "memory_context": {"preferred_hotel_class": "4_star"},
            }, {}, chain=chain)

        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0]["response_format"], {"type": "json_object"})
        instruction = next(message["content"] for message in requests[0]["messages"]
                           if message["role"] == "system" and "JSON schema:\n" in message["content"])
        schema = json.loads(instruction.split("JSON schema:\n", 1)[1])
        self.assertIn("updates", schema["properties"])
        self.assertIn("TravelPlanUpdates", schema["$defs"])
        self.assertEqual(result["travel_plan"].destination, "Paris")
        self.assertEqual(result["travel_plan"].preferred_hotel_class, "4_star")
        self.assertTrue(result["clarification_required"])
