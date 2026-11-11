from __future__ import annotations

from typing_extensions import NotRequired, TypedDict

from ..core import UNSET, Date, Optional, SdkBaseModel
from .enums.currency_code import CurrencyCodeOrStr
from .journal_entry_line import JournalEntryLine, JournalEntryLineDict


class JournalEntryRequest(SdkBaseModel):
    posting_date: Date
    reference_invoice_id: Optional[str] = UNSET
    paypal_transaction_id: Optional[str] = UNSET
    description: str
    currency: CurrencyCodeOrStr
    """ISO 4217 currency code."""

    lines: list[JournalEntryLine]


class JournalEntryRequestDict(TypedDict):
    posting_date: Date
    reference_invoice_id: NotRequired[str]
    paypal_transaction_id: NotRequired[str]
    description: str
    currency: CurrencyCodeOrStr
    lines: list[JournalEntryLineDict]
