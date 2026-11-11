from enum import Enum
from typing import Annotated, TypeAlias

from ...core import open_enum_validator


class AllowlistedTable(str, Enum):
    """Tables the LLM is allowed to query. Restricted to Silver (operational source of truth) and Gold (accounting
    evidence) layers. Bronze is excluded – raw payloads must never be exposed to the AI."""

    SILVER_PAYPAL_TRANSACTIONS = "silver_paypal_transactions"
    SILVER_ERP_INVOICES = "silver_erp_invoices"
    GOLD_RECONCILIATION_MATCHES = "gold_reconciliation_matches"
    GOLD_ANOMALY_FLAGS = "gold_anomaly_flags"
    GOLD_JOURNAL_HEADERS = "gold_journal_headers"
    GOLD_JOURNAL_LINES = "gold_journal_lines"

    __str__ = str.__str__


AllowlistedTableOrStr: TypeAlias = Annotated[AllowlistedTable | str, open_enum_validator(AllowlistedTable)]
