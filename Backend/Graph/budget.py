"""Compute a trip estimate from quoted prices, without asking an LLM to add."""

from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import re


def _amount(value):
    """Use decimal arithmetic; missing or invalid quotes are not zero prices."""
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return amount if amount.is_finite() and amount >= 0 else None


def _money(amount):
    return str(amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def build_budget(payload: dict, currency: str = "INR") -> dict:
    """Use one recommended flight/hotel and every suggested activity once.

    Travel prices normally arrive normalized to INR by currency_node. Never
    add a different currency without conversion, or multiply quoted totals by
    traveler count: the provider quote's coverage is not explicit in our schema.
    """
    rows = []
    total = Decimal("0")
    priced_count = 0

    def add(label, quote, field="price", note=None):
        nonlocal total, priced_count
        amount = _amount(quote.get(field))
        quoted_currency = str(quote.get("currency") or "").strip().upper()
        if amount is None:
            status = "Price not available"
        elif quoted_currency != currency:
            status = f"Price not available in {currency}"
            amount = None
        else:
            # Round each displayed line first so the displayed numbers add up.
            amount = amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            total += amount
            priced_count += 1
            status = note or "Quoted price"
        rows.append({"item": label, "amount": _money(amount) if amount is not None else None,
                     "note": status})

    flights = payload.get("flight_recommendations") or []
    hotels = payload.get("hotel_recommendations") or []
    activities = payload.get("activity_recommendations") or []
    add("Flight", flights[0]["flight"] if flights else {})

    hotel = dict(hotels[0]["hotel"]) if hotels else {}
    hotel_note = None
    if _amount(hotel.get("total_price")) is None:
        # Prefer the provider's stay total. Only derive a fallback from nightly
        # price when actual check-in/out dates establish the number of nights.
        plan = payload.get("travel_plan") or {}
        try:
            nights = (date.fromisoformat(plan["return_date"]) - date.fromisoformat(plan["departure_date"])).days
        except (KeyError, TypeError, ValueError):
            nights = 0
        nightly = _amount(hotel.get("price_per_night"))
        if nightly is not None and nights > 0:
            hotel["total_price"] = nightly * nights
            hotel_note = f"Estimated from nightly rate × {nights} nights"
    add("Hotel stay", hotel, "total_price", hotel_note)

    for index, recommendation in enumerate(activities, 1):
        add(f"Activity {index}", recommendation["activity"])
    if not activities:
        add("Activities", {})

    return {"currency": currency, "items": rows,
            "known_total": _money(total) if priced_count else None,
            "missing_prices": sum(row["amount"] is None for row in rows)}


def insert_budget(response: str, budget: dict) -> str:
    """Render the computed total even if the model omits budget information."""
    currency = budget["currency"]
    lines = ["### Total Budget Estimate", "", f"| Item | Cost ({currency}) |",
             "| --- | ---: |"]
    for row in budget["items"]:
        amount = row["amount"]
        cost = f"{Decimal(amount):,.2f}" if amount is not None else row["note"]
        lines.append(f"| {row['item']} | {cost} |")
    total = budget["known_total"]
    if total is not None:
        lines += ["", f"**Total estimated budget for priced items: {currency} {Decimal(total):,.2f}**"]
    else:
        lines += ["", "**Total budget unavailable: no usable prices were returned.**"]
    for row in budget["items"]:
        if row["note"].startswith("Estimated from"):
            lines += ["", f"Hotel stay: {row['note']}."]
    lines += ["", "This is a partial estimate. Unpriced items, meals, local transport, insurance, "
              "and other extras are not included. Quotes are used as returned; confirm traveler/room "
              "coverage and whether the flight quote includes the return journey."]
    block = "\n".join(lines)
    # Prefer placement before the conclusion; still show it when the model
    # uses a different heading or does not generate a conclusion at all.
    conclusion = re.search(r"(?m)^#{1,6}\s+Final Recommendation\s*$", response)
    if conclusion:
        return response[:conclusion.start()].rstrip() + "\n\n" + block + "\n\n" + response[conclusion.start():]
    return response.rstrip() + "\n\n" + block
