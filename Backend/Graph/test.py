import sys
from pathlib import Path
import asyncio

# Ensure workspace root is on sys.path so package imports work when
# running this script directly. The repository root is two levels up
# from this file: (.../AgenticAiTripPlannar)
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Backend.tools.flight_tool import search_flights


async def main():
    flights = await search_flights.ainvoke(
        {
            "origin": "AMD",
            "destination": "DEL",
            "departure_date": "2026-09-10",
            "return_date": "2026-09-15",
            "adults": 1,
            "currency": "INR",
            "travel_class": 1,
        }
    )

    print("Flights:", flights)


if __name__ == "__main__":
    asyncio.run(main())