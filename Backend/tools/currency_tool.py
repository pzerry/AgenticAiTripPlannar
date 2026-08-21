"""Currency conversion tool."""

from langchain_core.tools import tool

from Backend.Exceptions import CurrencyAPIError
from Backend.Logger.decorators import log_tool
from Backend.Logger.logger import get_logger
from Backend.integrations.currency_client import currency_client


logger = get_logger(__name__)


@tool
@log_tool("convert_currency")
async def convert_currency(amount: float, from_currency: str, to_currency: str) -> dict:
    """Convert an amount from one currency to another."""
    from_currency = from_currency.strip().upper()
    to_currency = to_currency.strip().upper()

    try:
        result = await currency_client.convert_currency(
            amount=amount,
            from_currency=from_currency,
            to_currency=to_currency,
        )
        return result.model_dump(mode="json")

    except CurrencyAPIError:
        logger.exception("Currency conversion failed: %s -> %s", from_currency, to_currency)

        return {
            "amount": amount,
            "from_currency": from_currency,
            "to_currency": to_currency,
            "exchange_rate": None,
            "converted_amount": None,
        }