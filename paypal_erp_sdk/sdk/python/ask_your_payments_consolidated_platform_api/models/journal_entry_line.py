from __future__ import annotations

from typing_extensions import NotRequired, TypedDict

from ..core import UNSET, Optional, SdkBaseModel


class JournalEntryLine(SdkBaseModel):
    account_code: str
    account_name: Optional[str] = UNSET
    debit: float
    credit: float
    memo: Optional[str] = UNSET


class JournalEntryLineDict(TypedDict):
    account_code: str
    account_name: NotRequired[str]
    debit: float
    credit: float
    memo: NotRequired[str]
