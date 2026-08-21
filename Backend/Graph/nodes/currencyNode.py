"""Currency conversion node for travel package pricing."""

from langchain_core.runnables import RunnableConfig

from Backend.Exceptions.exception import GraphStateError
from Backend.Graph.state import TravelAgentState
from Backend.Logger.logger import get_logger
from Backend.tools.currency_tool import convert_currency


logger = get_logger(__name__)


TARGET_CURRENCY = "INR"


async def currency_node(state: TravelAgentState, config: RunnableConfig) -> dict:
    """Convert every package pricing item into INR and calculate the final package total in INR."""
    packages = state.get("travel_packages")

    if not packages:
        raise GraphStateError("Currency node requires travel_packages.")

    converted_packages = []

    for package in packages:
        converted_total = 0.0
        converted_items = []

        # ==================================================
        # Convert every pricing item
        # ==================================================

        for item in package.pricing_items:
            if item.amount < 0:
                raise GraphStateError(f"Negative price found for {item.source}.")

            source_currency = item.currency.strip().upper()

            # --------------------------------------------------
            # Already INR
            # --------------------------------------------------

            if source_currency == TARGET_CURRENCY:
                converted_amount = float(item.amount)

            # --------------------------------------------------
            # Convert to INR
            # --------------------------------------------------

            else:
                result = await convert_currency.ainvoke(
                    {
                        "amount": item.amount,
                        "from_currency": source_currency,
                        "to_currency": TARGET_CURRENCY,
                    },
                    config=config,
                )

                converted_amount = result.get("converted_amount")

                if converted_amount is None:
                    raise GraphStateError(
                        f"Currency conversion failed for {item.amount} "
                        f"{source_currency} ({item.source})."
                    )

                converted_amount = float(converted_amount)

            # --------------------------------------------------
            # Create converted pricing item
            # --------------------------------------------------

            item_data = item.model_dump(mode="python")
            item_data["converted_amount"] = round(converted_amount, 2)
            item_data["converted_currency"] = TARGET_CURRENCY
            converted_items.append(item_data)
            converted_total += converted_amount

        # ==================================================
        # Update package
        # ==================================================

        package_data = package.model_dump(mode="python")
        package_data["pricing_items"] = converted_items
        package_data["converted_total_cost"] = round(converted_total, 2)
        package_data["converted_total_cost_currency"] = TARGET_CURRENCY
        converted_packages.append(package_data)

    logger.info(
        "Converted %d packages to %s.",
        len(converted_packages),
        TARGET_CURRENCY,
    )

    return {"travel_packages": converted_packages}