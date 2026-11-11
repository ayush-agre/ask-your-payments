from __future__ import annotations

from typing import Any

from typing_extensions import NotRequired, TypedDict

from ..core import UNSET, Optional, SdkBaseModel
from .enums.allowlisted_column1 import AllowlistedColumn1OrStr
from .enums.filter_operator2 import FilterOperator2OrStr


class FilterCondition(SdkBaseModel):
    """A single filter condition the LLM wants applied to the query."""

    column: AllowlistedColumn1OrStr
    """Column to filter on (must be from the whitelist)."""

    operator: FilterOperator2OrStr
    """Comparison operator."""

    value: Optional[Any] = UNSET
    """Filter value. Required for all operators except is_null/is_not_null. For 'in'/'not_in', provide a list. For
    'between', provide [low, high]."""


class FilterConditionDict(TypedDict):
    column: AllowlistedColumn1OrStr
    operator: FilterOperator2OrStr
    value: NotRequired[Any]
