from __future__ import annotations

from typing_extensions import NotRequired, TypedDict

from ..core import UNSET, Optional, SdkBaseModel
from .enums.allowlisted_column3 import AllowlistedColumn3OrStr
from .enums.sort_direction import SortDirectionOrStr


class SortSpec(SdkBaseModel):
    """A single sort specification."""

    column: AllowlistedColumn3OrStr
    """Column to sort by."""

    direction: Optional[SortDirectionOrStr] = UNSET
    """Sort direction."""


class SortSpecDict(TypedDict):
    column: AllowlistedColumn3OrStr
    direction: NotRequired[SortDirectionOrStr]
