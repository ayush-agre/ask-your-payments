from enum import Enum
from typing import Annotated, TypeAlias

from ...core import open_enum_validator


class InvoiceStatus(str, Enum):
    """Lifecycle status of an AP invoice."""

    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    PENDING_SETTLEMENT = "PENDING_SETTLEMENT"
    PAID = "PAID"
    DISPUTED = "DISPUTED"
    CANCELLED = "CANCELLED"

    __str__ = str.__str__


InvoiceStatusOrStr: TypeAlias = Annotated[InvoiceStatus | str, open_enum_validator(InvoiceStatus)]
