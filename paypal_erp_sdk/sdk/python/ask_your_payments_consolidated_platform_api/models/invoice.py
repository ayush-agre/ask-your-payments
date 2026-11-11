from __future__ import annotations

from pydantic import EmailStr
from typing_extensions import NotRequired, TypedDict

from ..core import UNSET, Date, OptionalNullable, SdkBaseModel
from .enums.currency_code import CurrencyCodeOrStr
from .enums.invoice_status import InvoiceStatusOrStr


class Invoice(SdkBaseModel):
    internal_invoice_id: str
    vendor_id: str
    vendor_name: str
    vendor_email: OptionalNullable[EmailStr] = UNSET
    invoice_date: Date
    due_date: Date
    erp_amount: float
    currency: CurrencyCodeOrStr
    """ISO 4217 currency code."""

    status: InvoiceStatusOrStr
    """Lifecycle status of an AP invoice."""


class InvoiceDict(TypedDict):
    internal_invoice_id: str
    vendor_id: str
    vendor_name: str
    vendor_email: NotRequired[EmailStr | None]
    invoice_date: Date
    due_date: Date
    erp_amount: float
    currency: CurrencyCodeOrStr
    status: InvoiceStatusOrStr
