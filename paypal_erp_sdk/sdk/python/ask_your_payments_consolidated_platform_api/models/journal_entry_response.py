from __future__ import annotations

from typing_extensions import NotRequired, TypedDict

from ..core import UNSET, Date, Optional, RFC3339DateTime, SdkBaseModel
from .enums.currency_code import CurrencyCodeOrStr
from .enums.status import StatusOrStr
from .journal_entry_line import JournalEntryLine, JournalEntryLineDict


class JournalEntryResponse(SdkBaseModel):
    journal_entry_id: str
    status: StatusOrStr
    posting_date: Date
    reference_invoice_id: Optional[str] = UNSET
    paypal_transaction_id: Optional[str] = UNSET
    description: Optional[str] = UNSET
    currency: CurrencyCodeOrStr
    """ISO 4217 currency code."""

    total_debit: float
    total_credit: float
    lines: list[JournalEntryLine]
    created_at: RFC3339DateTime


class JournalEntryResponseDict(TypedDict):
    journal_entry_id: str
    status: StatusOrStr
    posting_date: Date
    reference_invoice_id: NotRequired[str]
    paypal_transaction_id: NotRequired[str]
    description: NotRequired[str]
    currency: CurrencyCodeOrStr
    total_debit: float
    total_credit: float
    lines: list[JournalEntryLineDict]
    created_at: RFC3339DateTime
