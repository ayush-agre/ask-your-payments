from __future__ import annotations

from dataclasses import dataclass
from typing import Final, TypeAlias

from ..core import ErrorMapper, RawError, decode_json
from ..models.error import Error

CreateJournalEntryErrorBody: TypeAlias = Error | RawError


@dataclass(frozen=True, slots=True)
class _CreateJournalEntryError:
    def map(self, status_code: int, content: bytes) -> CreateJournalEntryErrorBody:
        match status_code:
            case 400 | 401 | 403 | 409 | 422 | 429 | 500:
                return decode_json[Error](content)
            case _:
                return RawError(status_code, content)


create_journal_entry_error_mapper: Final[ErrorMapper[CreateJournalEntryErrorBody]] = _CreateJournalEntryError()
