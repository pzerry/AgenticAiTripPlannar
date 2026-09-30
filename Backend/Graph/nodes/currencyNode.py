"""Currency conversion node for travel and direct currency requests."""

from copy import deepcopy

from langchain_core.runnables import RunnableConfig

from Backend.Exceptions.exception import GraphStateError
from Backend.Graph.state import TravelAgentState
from Backend.Logger.logger import get_logger
from Backend.Schemas.orchestrator_schema import TravelIntent
from Backend.tools.currency_tool import convert_currency

logger = get_logger(__name__)
TARGET_CURRENCY = "INR"


def _normalize_currency(currency: str | None) -> str:
    if not currency or not currency.strip():
        raise GraphStateError("Currency code is required for price conversion.")
    return currency.strip().upper()


def _validate_price(amount: float | None, source: str) -> float | None:
    if amount is None:
        return None

    amount = float(amount)
    if amount < 0:
        raise GraphStateError(f"Negative price found for {source}: {amount}")

    return amount


async def _get_exchange_rates(
    currencies: set[str],
    config: RunnableConfig,
) -> dict[str, float]:
    rates: dict[str, float] = {TARGET_CURRENCY: 1.0}
    currencies_to_convert = {
        currency for currency in currencies if currency != TARGET_CURRENCY
    }

    for source_currency in sorted(currencies_to_convert):
        result = await convert_currency.ainvoke(
            {
                "amount": 1.0,
                "from_currency": source_currency,
                "to_currency": TARGET_CURRENCY,
            },
            config=config,
        )

        exchange_rate = result.get("exchange_rate")
        if exchange_rate is None:
            raise GraphStateError(
                f"Currency conversion failed for {source_currency} -> {TARGET_CURRENCY}."
            )

        exchange_rate = float(exchange_rate)
        if exchange_rate <= 0:
            raise GraphStateError(
                f"Invalid exchange rate for {source_currency} -> {TARGET_CURRENCY}: {exchange_rate}"
            )

        rates[source_currency] = exchange_rate
        logger.info(
            "Exchange rate loaded: %s -> %s = %s",
            source_currency,
            TARGET_CURRENCY,
            exchange_rate,
        )

    return rates


def _convert_amount(
    amount: float,
    source_currency: str,
    rates: dict[str, float],
    source: str,
) -> float:
    rate = rates.get(source_currency)
    if rate is None:
        raise GraphStateError(
            f"No exchange rate available for {source_currency} ({source})."
        )
    return round(amount * rate, 2)


async def _handle_currency_request(
    state: TravelAgentState,
    config: RunnableConfig,
) -> dict:
    currency_request = state.get("currency_request")
    if currency_request is None:
        raise GraphStateError("Currency request is missing.")

    amount = _validate_price(currency_request.amount, "currency request")
    if amount is None:
        raise GraphStateError("Currency amount is required.")

    from_currency = _normalize_currency(currency_request.from_currency)
    to_currency = _normalize_currency(currency_request.to_currency)

    if from_currency == to_currency:
        result = {
            "amount": amount,
            "from_currency": from_currency,
            "to_currency": to_currency,
            "exchange_rate": 1.0,
            "converted_amount": amount,
        }
    else:
        result = await convert_currency.ainvoke(
            {
                "amount": amount,
                "from_currency": from_currency,
                "to_currency": to_currency,
            },
            config=config,
        )

        if result.get("converted_amount") is None:
            raise GraphStateError(
                f"Currency conversion failed for {amount} {from_currency} -> {to_currency}."
            )

        if result.get("exchange_rate") is None:
            raise GraphStateError(
                f"Exchange rate missing for {from_currency} -> {to_currency}."
            )

    logger.info(
        "Direct currency conversion completed: %s %s -> %s %s",
        amount,
        from_currency,
        result["converted_amount"],
        to_currency,
    )

    return {"currency": result}


async def _handle_travel_prices(
    state: TravelAgentState,
    config: RunnableConfig,
) -> dict:
    flights = state.get("flight_recommendations") or []
    hotels = state.get("hotel_recommendations") or []
    activities = state.get("activity_recommendations") or []

    currencies: set[str] = set()

    for recommendation in flights:
        flight = recommendation.flight
        price = _validate_price(flight.price, "flight")
        if price is not None:
            currencies.add(_normalize_currency(flight.currency))

    for recommendation in hotels:
        hotel = recommendation.hotel
        price_per_night = _validate_price(hotel.price_per_night, "hotel price_per_night")
        total_price = _validate_price(hotel.total_price, "hotel total_price")
        if price_per_night is not None or total_price is not None:
            currencies.add(_normalize_currency(hotel.currency))

    for recommendation in activities:
        activity = recommendation.activity
        price = _validate_price(activity.price, "activity")
        if price is not None:
            currencies.add(_normalize_currency(activity.currency))

    rates = await _get_exchange_rates(currencies, config)

    converted_flights = deepcopy(flights)
    for recommendation in converted_flights:
        flight = recommendation.flight
        price = _validate_price(flight.price, "flight")
        if price is None:
            continue

        source_currency = _normalize_currency(flight.currency)
        flight.price = _convert_amount(price, source_currency, rates, "flight")
        flight.currency = TARGET_CURRENCY

    converted_hotels = deepcopy(hotels)
    for recommendation in converted_hotels:
        hotel = recommendation.hotel
        source_currency = _normalize_currency(hotel.currency)

        if hotel.price_per_night is not None:
            price_per_night = _validate_price(hotel.price_per_night, "hotel price_per_night")
            if price_per_night is not None:
                hotel.price_per_night = _convert_amount(
                    price_per_night,
                    source_currency,
                    rates,
                    "hotel price_per_night",
                )

        if hotel.total_price is not None:
            total_price = _validate_price(hotel.total_price, "hotel total_price")
            if total_price is not None:
                hotel.total_price = _convert_amount(
                    total_price,
                    source_currency,
                    rates,
                    "hotel total_price",
                )

        hotel.currency = TARGET_CURRENCY

    converted_activities = deepcopy(activities)
    for recommendation in converted_activities:
        activity = recommendation.activity
        price = _validate_price(activity.price, "activity")
        if price is None:
            continue

        source_currency = _normalize_currency(activity.currency)
        activity.price = _convert_amount(price, source_currency, rates, "activity")
        activity.currency = TARGET_CURRENCY

    logger.info(
        "Travel price normalization completed. Currencies=%s, API calls=%d, target=%s",
        sorted(currencies),
        len([currency for currency in currencies if currency != TARGET_CURRENCY]),
        TARGET_CURRENCY,
    )

    return {
        "flight_recommendations": converted_flights,
        "hotel_recommendations": converted_hotels,
        "activity_recommendations": converted_activities,
    }


async def currency_node(
    state: TravelAgentState,
    config: RunnableConfig,
) -> dict:
    execution_plan = state.get("execution_plan")
    if execution_plan is None:
        raise GraphStateError("Execution plan is missing.")

    if execution_plan.intent == TravelIntent.CURRENCY_ONLY:
        return await _handle_currency_request(state, config)

    return await _handle_travel_prices(state, config)