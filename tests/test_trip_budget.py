"""Budget arithmetic and final-response integration without live provider calls."""

from importlib import import_module
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from langchain_core.messages import AIMessage

from Backend.Graph.budget import build_budget, insert_budget
from Backend.Schemas.orchestrator_schema import ExecutionPlan, TravelIntent, WorkerType
from Backend.Schemas.travel_schema import TravelPlan


def dubai_prices():
    return {
        "travel_plan": {"departure_date": "2026-10-12", "return_date": "2026-10-21"},
        "flight_recommendations": [{"flight": {"price": 28311.36, "currency": "INR"}}],
        "hotel_recommendations": [{"hotel": {"total_price": 86153.99, "price_per_night": 9558.31, "currency": "INR"}}],
        "activity_recommendations": [{"activity": {"name": "Desert safari", "price": None, "currency": None}}],
    }


class BudgetTests(unittest.TestCase):
    def test_reported_prices_use_stay_total_and_mark_unknown_activities(self):
        budget = build_budget(dubai_prices())
        self.assertEqual(budget["known_total"], "114465.35")
        self.assertEqual(budget["missing_prices"], 1)
        rendered = insert_budget("### Final Recommendation\nEnjoy your trip.", budget)
        self.assertIn("INR 114,465.35", rendered)
        self.assertIn("Price not available", rendered)
        self.assertLess(rendered.index("Total Budget Estimate"), rendered.index("Final Recommendation"))

    def test_alternatives_are_not_added_and_priced_activities_count_once(self):
        payload = dubai_prices()
        payload["flight_recommendations"].append({"flight": {"price": 99999, "currency": "INR"}})
        payload["hotel_recommendations"].append({"hotel": {"total_price": 99999, "currency": "INR"}})
        payload["activity_recommendations"] = [{"activity": {"price": 2000, "currency": "INR"}},
                                               {"activity": {"price": 0, "currency": "INR"}}]
        self.assertEqual(build_budget(payload)["known_total"], "116465.35")

    def test_nightly_fallback_uses_date_difference_not_day_count_or_adults(self):
        payload = dubai_prices()
        payload["travel_plan"].update(duration_days=10, adults=2)
        payload["hotel_recommendations"][0]["hotel"] = {"price_per_night": 1000, "currency": "INR"}
        budget = build_budget(payload)
        self.assertEqual(budget["items"][1]["amount"], "9000.00")
        self.assertIn("9 nights", budget["items"][1]["note"])
        payload["travel_plan"].pop("return_date")
        self.assertIsNone(build_budget(payload)["items"][1]["amount"])

    def test_mixed_currencies_invalid_prices_and_no_prices_are_not_summed(self):
        payload = dubai_prices()
        payload["flight_recommendations"][0]["flight"]["currency"] = "AED"
        payload["hotel_recommendations"][0]["hotel"] = {"total_price": float("nan"), "currency": "INR"}
        payload["activity_recommendations"][0]["activity"]["price"] = -10
        budget = build_budget(payload)
        self.assertIsNone(budget["known_total"])
        self.assertEqual(budget["missing_prices"], 3)
        self.assertIn("Total budget unavailable", insert_budget("Trip", budget))


class ResponseBudgetTests(unittest.IsolatedAsyncioTestCase):
    async def test_full_trip_inserts_computed_budget_even_when_model_omits_it(self):
        llm = SimpleNamespace(ainvoke=AsyncMock(return_value=AIMessage(content="### Final Recommendation\nEnjoy Dubai.")))
        with patch("Backend.LLM.factory.get_llm", return_value=llm):
            module = import_module("Backend.Graph.nodes.response_generator")
        state = dubai_prices()
        state["travel_plan"] = TravelPlan(departure_date="2026-10-12", return_date="2026-10-21")
        state["execution_plan"] = ExecutionPlan(intent=TravelIntent.FULL_PLAN, workers=[WorkerType.FLIGHT])
        with patch.object(module, "llm", llm):
            result = await module.response_generator(state, {})
        self.assertIn("INR 114,465.35", result["final_response"])
        self.assertIn('"known_total": "114465.35"', llm.ainvoke.call_args.args[0][1].content)

    async def test_direct_weather_response_does_not_include_stale_trip_costs(self):
        llm = SimpleNamespace(ainvoke=AsyncMock(return_value=AIMessage(content="Sunny.")))
        with patch("Backend.LLM.factory.get_llm", return_value=llm):
            module = import_module("Backend.Graph.nodes.response_generator")
        state = dubai_prices()
        state["execution_plan"] = ExecutionPlan(intent=TravelIntent.WEATHER_ONLY, workers=[WorkerType.WEATHER])
        with patch.object(module, "llm", llm):
            result = await module.response_generator(state, {})
        self.assertEqual(result["final_response"], "Sunny.")
