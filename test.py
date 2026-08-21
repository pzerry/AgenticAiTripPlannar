import asyncio
import time
from unittest.mock import AsyncMock, patch

from langchain_core.runnables import RunnableConfig

from Backend.Graph.agents.activity_agent import activity_agent
from Backend.Graph.agents.flight_agent import flight_agent
from Backend.Graph.agents.hotel_agent import hotel_agent

from Backend.Schemas.activity_schema import PlaceSummary
from Backend.Schemas.flight_schema import FlightOption
from Backend.Schemas.hotel_schema import HotelOption
from Backend.Schemas.travel_schema import TravelPlan

import Backend.Graph.agents.flight_agent as flight_module
import Backend.Graph.agents.hotel_agent as hotel_module
import Backend.Graph.agents.activity_agent as activity_module


# ==========================================================
# Mock API Results
# ==========================================================

def mock_flights() -> list[FlightOption]:
    return [
        FlightOption(
            airline="IndiGo",
            flight_number="6E5119",
            departure_airport="DEL",
            arrival_airport="AMD",
            departure_time="2026-09-10 05:10",
            arrival_time="2026-09-10 06:35",
            duration=85,
            stops=0,
            price=112.0,
            currency="USD",
        ),
        FlightOption(
            airline="Air India",
            flight_number="AI123",
            departure_airport="DEL",
            arrival_airport="AMD",
            departure_time="2026-09-10 09:00",
            arrival_time="2026-09-10 10:40",
            duration=100,
            stops=0,
            price=125.0,
            currency="USD",
        ),
        FlightOption(
            airline="IndiGo",
            flight_number="6E2341",
            departure_airport="DEL",
            arrival_airport="AMD",
            departure_time="2026-09-10 14:50",
            arrival_time="2026-09-10 16:20",
            duration=90,
            stops=0,
            price=112.0,
            currency="USD",
        ),
    ]


def mock_hotels() -> list[HotelOption]:
    return [
        HotelOption(
            name="Hyatt Regency Ahmedabad",
            price_per_night=45.0,
            total_price=225.0,
            currency="GBP",
            rating=4.4,
            reviews=14493,
            hotel_class="5-star hotel",
            address="Ahmedabad, India",
            amenities=[
                "Free Wi-Fi",
                "Free parking",
            ],
            check_in_time=None,
            check_out_time=None,
            free_cancellation=True,
        ),
        HotelOption(
            name="Taj Skyline Ahmedabad",
            price_per_night=58.0,
            total_price=290.0,
            currency="GBP",
            rating=4.5,
            reviews=9874,
            hotel_class="5-star hotel",
            address="Ahmedabad, India",
            amenities=[
                "Free Wi-Fi",
                "Pool",
                "Spa",
            ],
            check_in_time=None,
            check_out_time=None,
            free_cancellation=True,
        ),
        HotelOption(
            name="Courtyard Ahmedabad",
            price_per_night=40.0,
            total_price=200.0,
            currency="GBP",
            rating=4.2,
            reviews=7200,
            hotel_class="4-star hotel",
            address="Ahmedabad, India",
            amenities=[
                "Free Wi-Fi",
                "Breakfast",
            ],
            check_in_time=None,
            check_out_time=None,
            free_cancellation=True,
        ),
    ]


def mock_activities() -> list[PlaceSummary]:
    return [
        PlaceSummary(
            name="Sabarmati Riverfront",
            category="ATTRACTION",
            rating=4.4,
            reviews=2256,
            address="Ahmedabad, India",
            description="Scenic riverside attraction.",
            price=20.0,
            currency="USD",
        ),
        PlaceSummary(
            name="Adalaj Step-well",
            category="ATTRACTION",
            rating=4.3,
            reviews=1901,
            address="Adalaj, Gujarat, India",
            description="Historic step-well.",
            price=10.0,
            currency="EUR",
        ),
        PlaceSummary(
            name="Sidi Saiyyed Mosque",
            category="HISTORICAL",
            rating=4.5,
            reviews=3200,
            address="Ahmedabad, India",
            description="Historic mosque known for its architecture.",
            price=0.0,
            currency="INR",
        ),
    ]


# ==========================================================
# Mock Airport Resolver
# ==========================================================

async def mock_resolve_airports(
    origin: str,
    destination: str,
):
    return "DEL", "AMD"


# ==========================================================
# Test Travel Plan
# ==========================================================

travel_plan = TravelPlan(
    origin="Delhi",
    destination="Ahmedabad",
    departure_date="2026-09-10",
    return_date="2026-09-15",
    adults=1,
)


state = {
    "travel_plan": travel_plan,
}


config = RunnableConfig(
    configurable={
        "thread_id": "agent-selection-benchmark",
    }
)


# ==========================================================
# Flight Test
# ==========================================================

async def run_flight() -> float:

    print(
        "\n========== FLIGHT AGENT ==========",
        flush=True,
    )

    start = time.perf_counter()

    result = await flight_agent(
        state,
        config,
    )

    elapsed = time.perf_counter() - start

    recommendations = result.get(
        "flight_recommendations",
        [],
    )

    print(
        "Recommendations:",
        len(recommendations),
        flush=True,
    )

    for recommendation in recommendations:
        print(
            f"{recommendation.flight.airline} "
            f"{recommendation.flight.flight_number} | "
            f"{recommendation.flight.price} "
            f"{recommendation.flight.currency} | "
            f"{recommendation.reason}",
            flush=True,
        )

    print(
        f"TIME: {elapsed:.2f} seconds",
        flush=True,
    )

    return elapsed


# ==========================================================
# Hotel Test
# ==========================================================

async def run_hotel() -> float:

    print(
        "\n========== HOTEL AGENT ==========",
        flush=True,
    )

    start = time.perf_counter()

    result = await hotel_agent(
        state,
        config,
    )

    elapsed = time.perf_counter() - start

    recommendations = result.get(
        "hotel_recommendations",
        [],
    )

    print(
        "Recommendations:",
        len(recommendations),
        flush=True,
    )

    for recommendation in recommendations:
        print(
            f"{recommendation.hotel.name} | "
            f"{recommendation.hotel.total_price} "
            f"{recommendation.hotel.currency} | "
            f"{recommendation.reason}",
            flush=True,
        )

    print(
        f"TIME: {elapsed:.2f} seconds",
        flush=True,
    )

    return elapsed


# ==========================================================
# Activity Test
# ==========================================================

async def run_activity() -> float:

    print(
        "\n========== ACTIVITY AGENT ==========",
        flush=True,
    )

    start = time.perf_counter()

    result = await activity_agent(
        state,
        config,
    )

    elapsed = time.perf_counter() - start

    recommendations = result.get(
        "activity_recommendations",
        [],
    )

    print(
        "Recommendations:",
        len(recommendations),
        flush=True,
    )

    for recommendation in recommendations:
        print(
            f"{recommendation.activity.name} | "
            f"{recommendation.activity.rating} | "
            f"{recommendation.reason}",
            flush=True,
        )

    print(
        f"TIME: {elapsed:.2f} seconds",
        flush=True,
    )

    return elapsed


# ==========================================================
# Main
# ==========================================================

async def main():

    print(
        "\n"
        "==============================================\n"
        "     THREE AGENT SELECTION BENCHMARK\n"
        "==============================================\n"
        "REAL APIs: NO\n"
        "REAL LLM: YES\n"
        "==============================================\n",
        flush=True,
    )

    total_start = time.perf_counter()

    # ------------------------------------------------------
    # Patch imported module variables
    # ------------------------------------------------------

    flight_tool_mock = AsyncMock(
        return_value=mock_flights()
    )

    hotel_tool_mock = AsyncMock(
        return_value=mock_hotels()
    )

    activity_tool_mock = AsyncMock(
        return_value=mock_activities()
    )

    airport_mock = AsyncMock(
        side_effect=mock_resolve_airports
    )

    with (
        patch.object(
            flight_module,
            "search_flights",
            flight_tool_mock,
        ),
        patch.object(
            hotel_module,
            "search_hotels",
            hotel_tool_mock,
        ),
        patch.object(
            activity_module,
            "search_activities",
            activity_tool_mock,
        ),
        patch.object(
            flight_module.flight_client,
            "resolve_airports",
            airport_mock,
        ),
    ):

        flight_time = await run_flight()

        hotel_time = await run_hotel()

        activity_time = await run_activity()

    total_time = time.perf_counter() - total_start

    # ======================================================
    # Summary
    # ======================================================

    print(
        "\n==============================================",
        flush=True,
    )

    print(
        f"Flight Agent:   {flight_time:.2f} sec",
        flush=True,
    )

    print(
        f"Hotel Agent:    {hotel_time:.2f} sec",
        flush=True,
    )

    print(
        f"Activity Agent: {activity_time:.2f} sec",
        flush=True,
    )

    print(
        f"TOTAL:          {total_time:.2f} sec",
        flush=True,
    )

    print(
        "==============================================\n",
        flush=True,
    )


if __name__ == "__main__":
    asyncio.run(main())