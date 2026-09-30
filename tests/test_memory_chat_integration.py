"""Real PostgreSQL + production graph edges, with deterministic model boundaries.

These tests prove the wiring and persistence behavior, not LLM extraction quality
or live travel-provider availability. No application data or API keys are used.
"""

import asyncio
import json
import os
import time
import unittest
from unittest.mock import patch
from uuid import uuid4

from fastapi import FastAPI
import httpx
import jwt
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg import AsyncConnection, sql
from psycopg_pool import AsyncConnectionPool

from Backend.Graph.builder import build_travel_graph
from Backend.Graph.checkpoint import checkpoint_serializer
from Backend.Graph.nodes.travel_requester import analyze_request
from Backend.Memory.chat_turns import TurnBusyError
from Backend.Memory.events import DuplicateMessageError, OwnershipError
from Backend.Memory.extractor import ExtractionOutput, ExtractionResult, validate_proposals
from Backend.Memory.management import forget_preference
from Backend.Memory.migrate import apply_migrations, require_migrations
from Backend.Memory.semantic_memory import SemanticMemoryRepository
from Backend.Memory.worker import MemoryWorker
from Backend.Prompts.travel_request_analyzer_prompt import travel_request_analyzer_prompt
from Backend.Schemas.api_schema import ChatRequest
from Backend.Schemas.orchestrator_schema import ExecutionPlan, TravelIntent, WorkerType
from app.api.travel import router
from app.auth import Principal, get_verifier
from app.exception_handlers import register_exception_handlers
from app.services.travel_service import TravelService


class ScriptedAnalyzer:
    def __init__(self):
        self.calls = []
        self.fail_next = False
        self.entered = None
        self.release = None

    async def ainvoke(self, payload, config):
        self.calls.append(payload)
        if self.entered:
            self.entered.set()
            await self.release.wait()
        if self.fail_next:
            self.fail_next = False
            raise RuntimeError("simulated provider failure")
        latest = payload["messages"][-1].content
        updates = {}
        question = None
        if latest == "Help me plan":
            question = "Where would you like to go?"
        elif latest == "Paris. I always prefer 4 star hotels.":
            updates = {"destination": "Paris", "preferred_hotel_class": "4_star"}
            question = "When would you like to leave?"
        elif latest == "2026-10-10":
            updates = {"departure_date": "2026-10-10"}
        elif latest == "For this trip, use a 5 star hotel.":
            updates = {"preferred_hotel_class": "5_star"}
        return {"updates": updates, "clarification_required": bool(question),
                "clarification_questions": [question] if question else []}


class ScriptedExtractor:
    async def extract(self, context):
        # Only the fixture sentences below count as durable statements. The
        # production worker, evidence policy and ordered persistence still run.
        candidates = []
        if "I always prefer 4 star hotels." in context.text:
            candidates = [{"operation": "upsert", "memory_key": "preferred_hotel_class",
                "memory_value": "4_star", "subject": "self", "scope": "durable",
                "assertion": "explicit", "quote": "I always prefer 4 star hotels."}]
        return ExtractionResult(validate_proposals(context.text, ExtractionOutput(candidates=candidates)))


@unittest.skipUnless(os.getenv("MEMORY_TEST_DATABASE_URL"), "No test PostgreSQL URL")
class ChatIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.url = os.environ["MEMORY_TEST_DATABASE_URL"]
        self.schema = "chat_memory_" + uuid4().hex
        self.admin = await AsyncConnection.connect(self.url, autocommit=True)
        self.addAsyncCleanup(self.admin.close)
        await self.admin.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(self.schema)))
        self.addAsyncCleanup(self.drop_schema)
        await self.admin.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(self.schema)))
        await apply_migrations(self.admin)
        await require_migrations(self.admin)
        self.pool = AsyncConnectionPool(self.url, min_size=1, max_size=6, open=False,
            kwargs={"autocommit": True, "options": f"-c search_path={self.schema}"})
        await self.pool.open()
        self.addAsyncCleanup(self.pool.close)
        self.checkpointer = AsyncPostgresSaver(self.pool, serde=checkpoint_serializer())
        await self.checkpointer.setup()
        self.analyzer = ScriptedAnalyzer()

        async def analyze(state, config):
            return await analyze_request(state, config, chain=self.analyzer)

        async def orchestrate(state):
            return {"execution_plan": ExecutionPlan(intent=TravelIntent.WEATHER_ONLY, workers=[WorkerType.WEATHER])}

        async def noop(state):
            return {}

        async def respond(state):
            return {"final_response": json.dumps(state["travel_plan"].model_dump(mode="json"), sort_keys=True)}

        self.builder = build_travel_graph(node_overrides={
            "travel_request_analyzer": analyze, "orchestrator": orchestrate,
            "weather_node": noop, "flight_agent": noop, "hotel_agent": noop,
            "activity_agent": noop, "currency_node": noop, "response_generator": respond,
        })
        self.graph = self.builder.compile(checkpointer=self.checkpointer)
        self.service = TravelService(self.graph, self.pool)
        self.principal = Principal(uuid4())
        self.worker = MemoryWorker(self.pool, ScriptedExtractor())

    async def drop_schema(self):
        await self.admin.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(self.schema)))

    def request(self, text="Plan a trip", thread="a", **patches):
        return ChatRequest(**({"message_id": uuid4(), "thread_id": thread, "message": text} | patches))

    async def send(self, text="Plan a trip", thread="a"):
        request = self.request(text, thread)
        return request, await self.service.chat(request, self.principal)

    async def drain(self):
        for _ in range(20):
            if not await self.worker.run_once():
                return
        self.fail("Fixture queue did not drain")

    async def test_preference_crosses_threads_current_override_does_not_change_memory(self):
        await self.send("I always prefer 4 star hotels.")
        await self.drain()
        _, response = await self.send(thread="b")
        self.assertEqual(json.loads(response.response)["preferred_hotel_class"], "4_star")
        payload = self.analyzer.calls[-1]
        prompt = travel_request_analyzer_prompt.invoke(payload).to_string()
        self.assertIn('"preferred_hotel_class": "4_star"', prompt)
        _, response = await self.send("For this trip, use a 5 star hotel.", "b")
        self.assertEqual(json.loads(response.response)["preferred_hotel_class"], "5_star")
        await self.drain()
        _, response = await self.send(thread="c")
        self.assertEqual(json.loads(response.response)["preferred_hotel_class"], "4_star")

    async def test_clarifications_survive_recompile_and_old_retry_does_not_answer_next_question(self):
        first, initial = await self.send("Help me plan")
        self.assertTrue(initial.interrupted)
        self.service = TravelService(self.builder.compile(checkpointer=self.checkpointer), self.pool)
        second, reply = await self.send("Paris. I always prefer 4 star hotels.")
        self.assertTrue(reply.interrupted)
        calls = len(self.analyzer.calls)
        self.assertEqual((await self.service.chat(first, self.principal)).response, initial.response)
        self.assertEqual(len(self.analyzer.calls), calls)
        third, final = await self.send("2026-10-10")
        self.assertFalse(final.interrupted)
        self.assertEqual((await self.service.chat(second, self.principal)).response, reply.response)
        snapshot = await self.graph.aget_state({"configurable": {"thread_id": "a"}})
        messages = snapshot.values["messages"]
        self.assertEqual([m.id for m in messages if m.type == "human"],
                         [str(r.message_id) for r in (first, second, third)])
        self.assertEqual(len([m for m in messages if m.type == "ai"]), 3)
        await self.drain()
        _, response = await self.send(thread="b")
        self.assertEqual(json.loads(response.response)["preferred_hotel_class"], "4_star")

    async def test_lost_http_receipt_recovers_without_repeating_graph(self):
        request = self.request("Help me plan")
        with patch("app.services.travel_service.finish_turn", side_effect=RuntimeError("lost receipt")):
            with self.assertRaises(RuntimeError):
                await self.service.chat(request, self.principal)
        with self.assertRaises(TurnBusyError):
            await self.send("Paris")
        calls = len(self.analyzer.calls)
        response = await self.service.chat(request, self.principal)
        self.assertTrue(response.interrupted)
        self.assertEqual(len(self.analyzer.calls), calls)
        cursor = await self.admin.execute("SELECT count(*) FROM memory_events")
        self.assertEqual((await cursor.fetchone())[0], 1)

    async def test_failed_analyzer_retries_checkpoint_without_duplicate_message(self):
        self.analyzer.fail_next = True
        request = self.request()
        with self.assertRaises(RuntimeError):
            await self.service.chat(request, self.principal)
        response = await self.service.chat(request, self.principal)
        self.assertFalse(response.interrupted)
        snapshot = await self.graph.aget_state({"configurable": {"thread_id": "a"}})
        self.assertEqual(len([m for m in snapshot.values["messages"] if m.type == "human"]), 1)

    async def test_failed_analysis_after_clarification_retries_the_saved_answer(self):
        await self.send("Help me plan")
        request = self.request("Paris. I always prefer 4 star hotels.")
        self.analyzer.fail_next = True
        with self.assertRaises(RuntimeError):
            await self.service.chat(request, self.principal)
        response = await self.service.chat(request, self.principal)
        self.assertTrue(response.interrupted)
        self.assertIn("When", response.response)
        snapshot = await self.graph.aget_state({"configurable": {"thread_id": "a"}})
        self.assertEqual(len([m for m in snapshot.values["messages"] if m.id == str(request.message_id)]), 1)

    async def test_old_deletion_retry_does_not_delete_new_preference(self):
        deletion_id = uuid4()
        async with self.pool.connection() as conn:
            await forget_preference(conn, user_id=self.principal.user_id,
                                    memory_key="preferred_hotel_class", request_id=deletion_id)
        await self.send("I always prefer 4 star hotels.")
        await self.drain()
        async with self.pool.connection() as conn:
            await forget_preference(conn, user_id=self.principal.user_id,
                                    memory_key="preferred_hotel_class", request_id=deletion_id)
            rows = await SemanticMemoryRepository().get_all(conn, user_id=self.principal.user_id)
        self.assertEqual([row.memory_value for row in rows], ["4_star"])

    async def test_parallel_chat_is_rejected_then_same_id_replays(self):
        self.analyzer.entered, self.analyzer.release = asyncio.Event(), asyncio.Event()
        request = self.request()
        running = asyncio.create_task(self.service.chat(request, self.principal))
        try:
            await asyncio.wait_for(self.analyzer.entered.wait(), 5)
            with self.assertRaises(TurnBusyError):
                await self.service.chat(request, self.principal)
        finally:
            self.analyzer.release.set()
        first = await running
        self.assertEqual((await self.service.chat(request, self.principal)).response, first.response)

    async def test_delete_fences_pending_extraction_and_refreshes_only_memory_defaults(self):
        await self.send("I always prefer 4 star hotels.")
        await self.drain()
        await self.send(thread="default")
        await self.send("For this trip, use a 5 star hotel.", "explicit")
        await self.send("I always prefer 4 star hotels.", "pending")
        async with self.pool.connection() as conn:
            await forget_preference(conn, user_id=self.principal.user_id,
                                    memory_key="preferred_hotel_class", request_id=uuid4())
        await self.drain()
        _, response = await self.send("Continue", "default")
        self.assertIsNone(json.loads(response.response)["preferred_hotel_class"])
        _, response = await self.send("Continue", "explicit")
        self.assertEqual(json.loads(response.response)["preferred_hotel_class"], "5_star")
        async with self.pool.connection() as conn:
            self.assertEqual(await SemanticMemoryRepository().get_all(conn, user_id=self.principal.user_id), [])

    async def test_other_principal_and_reused_id_cannot_access_or_mutate_thread(self):
        request, _ = await self.send()
        other = Principal(uuid4())
        with self.assertRaises(OwnershipError):
            await self.service.chat(request, other)
        with self.assertRaises(OwnershipError):
            await self.service.debug_state("a", other)
        with self.assertRaises(OwnershipError):
            await self.service.chat(self.request(user_id=other.user_id), self.principal)
        with self.assertRaises(DuplicateMessageError):
            await self.service.chat(request.model_copy(update={"message": "changed"}), self.principal)

    async def test_http_authentication_memory_status_and_deletion(self):
        app = FastAPI()
        app.state.travel_service = self.service
        app.include_router(router)
        register_exception_handlers(app)
        secret = "integration-test-secret-32-bytes-minimum"
        auth_env = {"APP_ENV": "development", "TRAVEL_AUTH_MODE": "development", "TRAVEL_DEV_JWT_SECRET": secret}

        def token(user):
            return jwt.encode({"sub": str(user), "iat": int(time.time()), "exp": int(time.time()) + 60,
                "iss": "trip-planner-development", "aud": "trip-planner"}, secret, algorithm="HS256")

        get_verifier.cache_clear()
        self.addCleanup(get_verifier.cache_clear)
        with patch.dict(os.environ, auth_env):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                for url in ("/travel/me", "/travel/memories", "/travel/debug/state/a"):
                    self.assertEqual((await client.get(url)).status_code, 401)
                self.assertEqual((await client.post("/travel/chat", json=self.request().model_dump(mode="json"))).status_code, 401)
                client.headers["Authorization"] = "Bearer " + token(self.principal.user_id)
                request = self.request("I always prefer 4 star hotels.")
                response = await client.post("/travel/chat", json=request.model_dump(mode="json"))
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(response.json()["memory_status"], "pending")
                await self.drain()
                status = await client.get(f"/travel/memory-events/{request.message_id}")
                self.assertEqual(status.json()["status"], "complete")
                self.assertEqual(len((await client.get("/travel/memories")).json()["memories"]), 1)
                deletion_id = str(uuid4())
                for _ in range(2):
                    deleted = await client.delete("/travel/memories/preferred_hotel_class",
                                                  headers={"Idempotency-Key": deletion_id})
                    self.assertEqual(deleted.status_code, 204, deleted.text)
                self.assertEqual((await client.get("/travel/memories")).json()["memories"], [])
                client.headers["Authorization"] = "Bearer " + token(uuid4())
                self.assertEqual((await client.post("/travel/chat", json=request.model_dump(mode="json"))).status_code, 404)
                self.assertEqual((await client.get("/travel/debug/state/a")).status_code, 404)
                self.assertEqual((await client.get(f"/travel/memory-events/{request.message_id}")).status_code, 404)
                self.assertEqual((await client.get("/travel/memories")).json()["memories"], [])
