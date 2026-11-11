from __future__ import annotations

from typing_extensions import NotRequired, TypedDict

from ..core import UNSET, Optional, SdkBaseModel
from .enums.aggregate_function import AggregateFunctionOrStr
from .enums.allowlisted_column import AllowlistedColumnOrStr
from .enums.allowlisted_column2 import AllowlistedColumn2OrStr


class GroupSpec(SdkBaseModel):
    """A grouping specification for server-side grouping in AG Grid."""

    column: AllowlistedColumn2OrStr
    """Column to group by."""

    aggregate: Optional[AggregateFunctionOrStr] = UNSET
    """Aggregate function to apply to grouped rows."""

    aggregate_column: Optional[AllowlistedColumnOrStr] = UNSET
    """Column to aggregate (required if aggregate is set)."""


class GroupSpecDict(TypedDict):
    column: AllowlistedColumn2OrStr
    aggregate: NotRequired[AggregateFunctionOrStr]
    aggregate_column: NotRequired[AllowlistedColumnOrStr]
