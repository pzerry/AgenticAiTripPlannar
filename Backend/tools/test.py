# test_flight_agent.py
import asyncio
import sys
from pathlib import Path

# Add the project root to PYTHONPATH if needed
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from Backend.Graph.state import TravelAgentState
from Backend.Graph.agents.flight_agent import flight_agent
from Backend.Schemas.travel_schema import TravelPlan
from langchain_core.runnables import RunnableConfig


async def test_flight_agent():
    # Create a dummy TravelPlan with required fields
    plan = TravelPlan(
        origin="DEL",
        destination="NRT",
        departure_date="2026-08-15",
        return_date="2026-08-22",
        adults=1,
        destination_currency="USD",  # for flight price display
        # other fields can be left None
    )

    # Build the state dictionary (as expected by the agent)
    state: TravelAgentState = {
        "travel_plan": plan,
        # other keys are not needed for flight_agent
        "messages": [],
        "clarification_required": False,
        "clarification_question": None,
        "user_preferences": None,
        "execution_plan": None,
        "flights": None,
        "hotels": None,
        "activities": None,
        "weather": None,
        "currency": None,
        "travel_packages": None,
        "final_response": None,
        "runtime_errors": [],
    }

    # Empty config (thread_id is optional for testing)
    config = RunnableConfig(configurable={"thread_id": "test-123"})

    # Invoke the agent
    try:
        result = await flight_agent(state, config)
        print("Flight agent returned:")
        print(f"Number of flights selected: {len(result.get('flights', []))}")
        for i, flight in enumerate(result.get("flights", []), 1):
            print(f"\nFlight {i}:")
            print(f"  Airline: {flight.airline}")
            print(f"  Flight #: {flight.flight_number}")
            print(f"  Departure: {flight.departure_airport} at {flight.departure_time}")
            print(f"  Arrival: {flight.arrival_airport} at {flight.arrival_time}")
            print(f"  Duration: {flight.duration}")
            print(f"  Stops: {flight.stops}")
            print(f"  Price: {flight.price}")
    except Exception as e:
        print(f"Error during flight_agent execution: {e}")


if __name__ == "__main__":
    asyncio.run(test_flight_agent())