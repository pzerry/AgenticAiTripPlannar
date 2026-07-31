import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from integrations.activity_client import activity_client


async def main():
    print("\n" + "=" * 80)
    print("TRIPADVISOR PLACE SEARCH")
    print("=" * 80)

    places = await activity_client.search_places(
        query="Eiffel Tower",
        location="Paris",
    )

    if not places:
        print("No places found.")
        return

    for index, place in enumerate(places, start=1):
        print(f"\nResult {index}")
        print(f"Place ID  : {place.place_id}")
        print(f"Name      : {place.name}")
        print(f"Category  : {place.category}")
        print(f"Rating    : {place.rating}")
        print(f"Reviews   : {place.reviews}")
        print(f"Address   : {place.address}")
        print(f"Thumbnail : {place.thumbnail}")

    print("\n" + "=" * 80)
    print("PLACE DETAILS")
    print("=" * 80)

    details = await activity_client.get_place_details(
        place_id=places[0].place_id,
    )

    print(f"Place ID    : {details.place_id}")
    print(f"Name        : {details.name}")
    print(f"Category    : {details.category}")
    print(f"Rating      : {details.rating}")
    print(f"Reviews     : {details.reviews}")
    print(f"Address     : {details.address}")
    print(f"Website     : {details.website}")
    print(f"Phone       : {details.phone}")
    print(f"Description : {details.description}")

    print("\nOpening Hours")
    for hour in details.opening_hours:
        print(f"  {hour.day}: {hour.hours}")

    print(f"\nImages               : {len(details.images)}")
    print(f"Nearby Hotels        : {len(details.nearby_hotels)}")
    print(f"Nearby Restaurants   : {len(details.nearby_restaurants)}")
    print(f"Nearby Attractions   : {len(details.nearby_attractions)}")


if __name__ == "__main__":
    asyncio.run(main())