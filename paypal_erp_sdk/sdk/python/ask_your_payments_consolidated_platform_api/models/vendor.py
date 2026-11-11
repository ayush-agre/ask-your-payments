from __future__ import annotations

from pydantic import EmailStr
from typing_extensions import NotRequired, TypedDict

from ..core import UNSET, Optional, OptionalNullable, SdkBaseModel
from .enums.currency_code import CurrencyCodeOrStr


class Vendor(SdkBaseModel):
    vendor_id: str
    vendor_name: str
    vendor_email: OptionalNullable[EmailStr] = UNSET
    gstin: Optional[str] = UNSET
    pan: Optional[str] = UNSET
    payment_terms_days: int
    default_currency: CurrencyCodeOrStr
    """ISO 4217 currency code."""

    active: bool


class VendorDict(TypedDict):
    vendor_id: str
    vendor_name: str
    vendor_email: NotRequired[EmailStr | None]
    gstin: NotRequired[str]
    pan: NotRequired[str]
    payment_terms_days: int
    default_currency: CurrencyCodeOrStr
    active: bool
