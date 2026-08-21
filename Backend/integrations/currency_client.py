"""Client for ExchangeRate API."""

from __future__ import annotations

import httpx

from Backend.Config import config
from Backend.Config.env import env
from Backend.Exceptions import ConfigurationError, CurrencyAPIError
from Backend.Logger.decorators import log_api
from Backend.Logger.logger import get_logger
from Backend.Schemas.currency_schema import CurrencyConversion


logger = get_logger(__name__)


class CurrencyClient:
    """Client for ExchangeRate API."""

    def __init__(self) -> None:
        self.base_url = config["currency"]["base_url"]
        self.timeout = config["currency"]["timeout"]
        self.api_key = env.EXCHANGE_RATE_API_KEY

        if not self.api_key:
            raise ConfigurationError("EXCHANGE_RATE_API_KEY is missing.")

    @log_api("ExchangeRate")
    async def convert_currency(self, amount: float, from_currency: str, to_currency: str) -> CurrencyConversion:
        """Convert an amount from one currency to another."""
        if amount < 0:
            raise CurrencyAPIError("Amount cannot be negative.")

        if not from_currency or not from_currency.strip():
            raise CurrencyAPIError("Source currency is required.")

        if not to_currency or not to_currency.strip():
            raise CurrencyAPIError("Target currency is required.")

        from_currency = from_currency.strip().upper()
        to_currency = to_currency.strip().upper()

        url = f"{self.base_url}/{self.api_key}/pair/{from_currency}/{to_currency}/{amount}"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()

        except httpx.TimeoutException as exc:
            logger.exception("Currency API request timed out.")
            raise CurrencyAPIError("Currency service timed out.") from exc

        except httpx.HTTPStatusError as exc:
            logger.exception("Currency API returned %s\n%s", exc.response.status_code, exc.response.text)
            raise CurrencyAPIError(f"Currency API Error ({exc.response.status_code}): {exc.response.text}") from exc

        except httpx.RequestError as exc:
            logger.exception("Unable to reach Currency API.")
            raise CurrencyAPIError("Unable to reach Currency API.") from exc

        if data.get("result") != "success":
            raise CurrencyAPIError(data.get("error-type", "Currency conversion failed."))

        try:
            exchange_rate = float(data["conversion_rate"])
            converted_amount = float(data["conversion_result"])

        except (KeyError, TypeError, ValueError) as exc:
            logger.exception("Invalid currency response.")
            raise CurrencyAPIError("Currency API returned an invalid response.") from exc

        logger.info(
            "Currency converted successfully: %s %s -> %s %s",
            amount,
            from_currency,
            converted_amount,
            to_currency,
        )

        return CurrencyConversion(
            amount=amount,
            from_currency=from_currency,
            to_currency=to_currency,
            exchange_rate=exchange_rate,
            converted_amount=converted_amount,
        )


currency_client = CurrencyClient()