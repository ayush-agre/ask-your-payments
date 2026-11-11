from enum import Enum
from typing import Annotated, TypeAlias

from ...core import open_enum_validator


class CurrencyCode(str, Enum):
    """ISO 4217 currency code."""

    INR = "INR"
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    AED = "AED"
    SGD = "SGD"

    __str__ = str.__str__


CurrencyCodeOrStr: TypeAlias = Annotated[CurrencyCode | str, open_enum_validator(CurrencyCode)]
