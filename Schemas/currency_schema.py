from typing import Optional
from pydantic import BaseModel, Field

class CurrencyConversion(BaseModel):
   amount: float = Field(description="Amount to be converted from the source currency.")
   from_currency: str = Field(description="ISO 4217 code of the source currency.")
   to_currency: str = Field(description="ISO 4217 code of the target currency.")
   exchange_rate: float = Field(description="Exchange rate used to convert the source currency to the target currency.")
   converted_amount: float = Field(description="Final converted amount in the target currency.")