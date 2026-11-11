from __future__ import annotations

from typing_extensions import NotRequired, TypedDict

from ..core import UNSET, Optional, SdkBaseModel
from .enums.allowlisted_table import AllowlistedTableOrStr
from .enums.allowlisted_table1 import AllowlistedTable1OrStr
from .filter_condition import FilterCondition, FilterConditionDict
from .group_spec import GroupSpec, GroupSpecDict
from .sort_spec import SortSpec, SortSpecDict


class InvestigationIntent(SdkBaseModel):
    """The AI-to-Grid Contract – the ONLY schema Gemini is allowed to produce.

    This Pydantic model is the physical decoupling boundary between probabilistic AI reasoning and deterministic
    financial execution. The LLM produces structured intent; the Read-Only Query Compiler translates it into
    allowlisted, parameterised SQLAlchemy queries.

    The LLM NEVER sees or produces SQL."""

    target_table: AllowlistedTable1OrStr
    """Primary table to query. The LLM selects from the allowlisted Silver/Gold tables only."""

    join_tables: Optional[list[AllowlistedTableOrStr]] = UNSET
    """Additional tables to JOIN (the compiler resolves FK relationships)."""

    filters: Optional[list[FilterCondition]] = UNSET
    """WHERE clause conditions. All are ANDed together."""

    sorts: Optional[list[SortSpec]] = UNSET
    """ORDER BY specifications."""

    groups: Optional[list[GroupSpec]] = UNSET
    """GROUP BY with optional aggregates for the SSRM datasource."""

    limit: int = 100
    """Maximum rows to return (maps to AG Grid block size)."""

    offset: int = 0
    """Pagination offset."""

    explanation: str
    """Human-readable explanation of what this investigation does, suitable for display in the AG Grid Investigation
    Studio."""

    suggested_actions: Optional[list[str]] = UNSET
    """Recommended follow-up actions for the FinOps manager."""


class InvestigationIntentDict(TypedDict):
    target_table: AllowlistedTable1OrStr
    join_tables: NotRequired[list[AllowlistedTableOrStr]]
    filters: NotRequired[list[FilterConditionDict]]
    sorts: NotRequired[list[SortSpecDict]]
    groups: NotRequired[list[GroupSpecDict]]
    limit: NotRequired[int]
    offset: NotRequired[int]
    explanation: str
    suggested_actions: NotRequired[list[str]]
