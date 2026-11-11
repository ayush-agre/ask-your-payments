from enum import Enum
from typing import Annotated, TypeAlias

from ...core import open_enum_validator


class MatchStatus(str, Enum):
    """Lifecycle state of a match."""

    MATCHED = "matched"
    PARTIAL = "partial"
    UNMATCHED = "unmatched"
    DISPUTED = "disputed"
    REVIEW_REQUIRED = "review_required"

    __str__ = str.__str__


MatchStatusOrStr: TypeAlias = Annotated[MatchStatus | str, open_enum_validator(MatchStatus)]
