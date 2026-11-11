from enum import Enum
from typing import Annotated, TypeAlias

from ...core import open_enum_validator


class AllowlistedTable1(str, Enum):
    """Primary table to query. The LLM selects from the allowlisted Silver/Gold tables only."""

    SILVER_PAYPAL_TRANSACTIONS = "silver_paypal_transactions"
    SILVER_ERP_INVOICES = "silver_erp_invoices"
    GOLD_RECONCILIATION_MATCHES = "gold_reconciliation_matches"
    GOLD_ANOMALY_FLAGS = "gold_anomaly_flags"
    GOLD_JOURNAL_HEADERS = "gold_journal_headers"
    GOLD_JOURNAL_LINES = "gold_journal_lines"

    __str__ = str.__str__


AllowlistedTable1OrStr: TypeAlias = Annotated[AllowlistedTable1 | str, open_enum_validator(AllowlistedTable1)]
