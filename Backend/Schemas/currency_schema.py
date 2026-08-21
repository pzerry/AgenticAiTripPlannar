"""Currency schemas."""

from pydantic import BaseModel, Field
from typing import Literal

from typing import Literal

from pydantic import BaseModel, Field


class PricingItem(BaseModel):
    """Source and converted price for a package component."""

    amount: float = Field(description="Original price amount.")
    currency: str = Field(description="ISO 4217 source currency code.")
    source: Literal["FLIGHT", "HOTEL", "ACTIVITY"] = Field(description="Travel component that produced the price.")
    converted_amount: float | None = Field(default=None, ge=0, description="Price converted to INR.")
    converted_currency: str | None = Field(default=None, description="Currency of converted_amount.")

class CurrencyConversion(BaseModel):
    """Result of a currency conversion."""

    amount: float = Field(description="Amount to be converted.")
    from_currency: str = Field(description="ISO 4217 source currency code.")
    to_currency: str = Field(description="ISO 4217 target currency code.")
    exchange_rate: float = Field(description="Exchange rate used for conversion.")
    converted_amount: float = Field(description="Converted amount in the target currency.")

class CurrencyRequest(BaseModel):
    """Request to convert an amount between two currencies."""

    amount: float = Field(description="Amount to convert.")
    from_currency: str = Field(description="ISO 4217 source currency code.")
    to_currency: str = Field(description="ISO 4217 target currency code.")