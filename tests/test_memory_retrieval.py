import unittest

from Backend.Memory.retrieval import merge_plan_with_memory
from Backend.Schemas.travel_schema import TravelPlan


class RetrievalTests(unittest.TestCase):
    def test_new_trip_gets_defaults(self):
        memory = {"preferred_flight_type": "non_stop", "preferred_trip_style": "budget_friendly"}
        plan, applied = merge_plan_with_memory(None, {"destination": "Paris"}, memory)
        self.assertEqual(plan.preferred_flight_type, "non_stop")
        self.assertEqual(plan.preferred_trip_style, "budget_friendly")
        self.assertEqual(plan.destination, "Paris")
        self.assertEqual(applied, memory)

    def test_trip_exception_wins_and_does_not_change_profile(self):
        memory = {"preferred_flight_type": "non_stop"}
        plan, applied = merge_plan_with_memory(None,
            {"preferred_flight_type": "connecting_allowed"}, memory)
        self.assertEqual(plan.preferred_flight_type, "connecting_allowed")
        self.assertEqual(applied, {})
        self.assertEqual(memory, {"preferred_flight_type": "non_stop"})

    def test_existing_explicit_trip_value_is_preserved(self):
        plan, _ = merge_plan_with_memory(TravelPlan(preferred_hotel_class="3_star"), {},
                                         {"preferred_hotel_class": "5_star"})
        self.assertEqual(plan.preferred_hotel_class, "3_star")

    def test_forgetting_removes_only_memory_defaults(self):
        plan = TravelPlan(preferred_flight_type="non_stop", preferred_hotel_class="4_star")
        plan, applied = merge_plan_with_memory(plan, {}, {}, {"preferred_flight_type": "non_stop"})
        self.assertIsNone(plan.preferred_flight_type)
        self.assertEqual(plan.preferred_hotel_class, "4_star")
        self.assertEqual(applied, {})

    def test_explicit_same_value_becomes_trip_owned(self):
        plan, applied = merge_plan_with_memory(TravelPlan(preferred_flight_type="non_stop"),
            {"preferred_flight_type": "non_stop"}, {"preferred_flight_type": "non_stop"},
            {"preferred_flight_type": "non_stop"})
        self.assertEqual(applied, {})
        plan, _ = merge_plan_with_memory(plan, {}, {}, applied)
        self.assertEqual(plan.preferred_flight_type, "non_stop")

    def test_bad_memory_cannot_populate_arbitrary_plan_fields(self):
        plan, applied = merge_plan_with_memory(None, {}, {"destination": "invented", "preferred_hotel_class": "unsafe"})
        self.assertIsNone(plan.destination)
        self.assertIsNone(plan.preferred_hotel_class)
        self.assertEqual(applied, {})
