import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from Backend.Memory.contracts import MessageContext
from Backend.Memory.extractor import ExtractionOutput, ProposedPreference, StructuredExtractor, validate_proposals


class ExtractorTests(unittest.IsolatedAsyncioTestCase):
    def proposal(self, quote):
        return ProposedPreference(operation="upsert", memory_key="preferred_flight_type",
            memory_value="non_stop", subject="self", scope="durable", assertion="explicit", quote=quote)

    def context(self, **patch):
        return MessageContext(**(dict(user_id=uuid4(), message_id=uuid4(), thread_id="a",
            sequence=1, occurred_at=datetime.now(timezone.utc), role="user",
            text="I always prefer nonstop flights.") | patch))

    def test_offsets_are_computed_with_unicode(self):
        quote = "I always prefer nonstop flights."
        candidates = validate_proposals("✈️ " + quote, ExtractionOutput(candidates=[self.proposal(quote)]))
        self.assertEqual(candidates[0].evidence.start, 3)

    def test_ambiguous_or_missing_evidence_is_rejected(self):
        for text in ("hello", "nonstop nonstop"):
            with self.assertRaises(ValueError):
                validate_proposals(text, ExtractionOutput(candidates=[self.proposal("nonstop")]))

    async def test_non_user_sources_never_call_model(self):
        model = Mock()
        extractor = StructuredExtractor(model)
        for role in ("assistant", "tool", "system"):
            self.assertEqual((await extractor.extract(self.context(role=role))).candidates, [])
        model.with_structured_output.return_value.ainvoke.assert_not_called()

    async def test_model_receives_no_identity_and_usage_is_bounded(self):
        context = self.context()
        model = Mock()
        model.with_structured_output.return_value.ainvoke = AsyncMock(return_value={
            "parsed": ExtractionOutput(candidates=[self.proposal(context.text)]),
            "raw": Mock(usage_metadata={"input_tokens": 12, "output_tokens": 5, "private": "no"},
                        response_metadata={"finish_reason": "stop"}),
            "parsing_error": None,
        })
        result = await StructuredExtractor(model).extract(context)
        self.assertEqual(len(result.candidates), 1)
        self.assertEqual(result.usage, {"input_tokens": 12, "output_tokens": 5})
        sent = model.with_structured_output.return_value.ainvoke.call_args.args[0]
        self.assertNotIn(str(context.user_id), str(sent))
        self.assertNotIn(str(context.message_id), str(sent))

    async def test_invalid_model_output_fails_closed(self):
        model = Mock()
        model.with_structured_output.return_value.ainvoke = AsyncMock(return_value={
            "parsed": None, "parsing_error": ValueError("bad")})
        with self.assertRaises(ValueError):
            await StructuredExtractor(model).extract(self.context())
