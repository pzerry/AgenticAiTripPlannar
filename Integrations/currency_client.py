import os

import httpx
from dotenv import load_dotenv

from Config import config
from Exceptions import ConfigurationError, CurrencyAPIError
from Logger import logger
from Schemas.currency_schema import CurrencyConversion

load_dotenv()


class CurrencyClient:
    """Client for Exchange Rate API."""

    def __init__(self):
        self.base_url = config["currency"]["base_url"]
        self.timeout = config["currency"]["timeout"]

        self.api_key = os.getenv("EXCHANGE_RATE_API_KEY")

        if not self.api_key:
            raise ConfigurationError(
                "EXCHANGE_RATE_API_KEY is missing."
            )

    async def convert_currency(
        self,
        amount: float,
        from_currency: str,
        to_currency: str,
    ) -> CurrencyConversion:
        """
        Convert money from one currency into another.
        """

        url = (
            f"{self.base_url}/"
            f"{self.api_key}/pair/"
            f"{from_currency.upper()}/"
            f"{to_currency.upper()}/"
            f"{amount}"
        )

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout
            ) as client:

                response = await client.get(url)

            response.raise_for_status()

        except httpx.TimeoutException as e:
            logger.exception("Currency API timed out.")
            raise CurrencyAPIError(
                "Currency service timed out."
            ) from e

        except httpx.HTTPStatusError as e:
            logger.exception("Currency API returned error.")
            raise CurrencyAPIError(
                "Currency service returned an error."
            ) from e

        except httpx.RequestError as e:
            logger.exception("Unable to connect to Currency API.")
            raise CurrencyAPIError(
                "Unable to connect to currency service."
            ) from e

        data = response.json()

        if data["result"] != "success":
            raise CurrencyAPIError(
                data.get("error-type", "Currency conversion failed.")
            )

        return CurrencyConversion(
            amount=amount,
            from_currency=from_currency.upper(),
            to_currency=to_currency.upper(),
            exchange_rate=data["conversion_rate"],
            converted_amount=data["conversion_result"],
        )


currency_client = CurrencyClient()