from __future__ import annotations

from typing import Any

from typing_extensions import NotRequired, TypedDict

from ..core import UNSET, Optional, RFC3339DateTime, SdkBaseModel
from .investigation_intent1 import InvestigationIntent1, InvestigationIntent1Dict
from .investigation_result_row import InvestigationResultRow, InvestigationResultRowDict


class InvestigationResponse(SdkBaseModel):
    """Complete response from the AI Investigation pipeline."""

    investigation_id: Optional[str] = UNSET
    """Unique identifier for this investigation."""

    original_query: str
    """The user's original query (PII-scrubbed)."""

    ai_explanation: str
    """Gemini's human-readable explanation of the investigation."""

    suggested_actions: Optional[list[str]] = UNSET
    """AI-suggested follow-up actions."""

    intent: InvestigationIntent1
    """The structured AI-to-Grid Contract that was compiled."""

    columns: list[str]
    """Ordered list of column names in the result set."""

    rows: Optional[list[InvestigationResultRow]] = UNSET
    """Result rows."""

    total_count: int = 0
    """Total rows matching (before pagination)."""

    kpi: Optional[Any] = UNSET
    """Pre-computed KPI aggregates: total_trapped_working_capital, dollars_reconciled, dollars_requiring_review."""

    pii_scrubbed: bool = False
    """Whether PII minimisation was applied."""

    pii_categories: Optional[list[str]] = UNSET
    """PII categories that were detected and scrubbed."""

    executed_at: Optional[RFC3339DateTime] = UNSET
    """Timestamp of query execution."""

    query_duration_ms: Optional[float] = UNSET
    """Database query execution time in milliseconds."""


class InvestigationResponseDict(TypedDict):
    investigation_id: NotRequired[str]
    original_query: str
    ai_explanation: str
    suggested_actions: NotRequired[list[str]]
    intent: InvestigationIntent1Dict
    columns: list[str]
    rows: NotRequired[list[InvestigationResultRowDict]]
    total_count: NotRequired[int]
    kpi: NotRequired[Any]
    pii_scrubbed: NotRequired[bool]
    pii_categories: NotRequired[list[str]]
    executed_at: NotRequired[RFC3339DateTime]
    query_duration_ms: NotRequired[float]
