from langchain_core.tools import tool

from Integrations.currency_client import currency_client


@tool
async def convert_currency(
    amount: float,
    from_currency: str,
    to_currency: str,
) -> dict:
    """
    Convert an amount from one currency to another.

    Args:
        amount: Amount to convert.
        from_currency: Source ISO currency code (USD, INR, EUR).
        to_currency: Target ISO currency code.

    Returns:
        Converted currency information.
    """

    result = await currency_client.convert_currency(
        amount=amount,
        from_currency=from_currency,
        to_currency=to_currency,
    )

    return result.model_dump()

