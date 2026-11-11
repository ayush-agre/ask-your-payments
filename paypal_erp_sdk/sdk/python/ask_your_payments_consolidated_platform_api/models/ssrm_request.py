from __future__ import annotations

from typing import Any

from pydantic import Field
from typing_extensions import NotRequired, TypedDict

from ..core import UNSET, Optional, SdkBaseModel


class SsrmRequest(SdkBaseModel):
    """AG Grid Server-Side Row Model request shape."""

    start_row: int = Field(default=0, alias="startRow")
    end_row: int = Field(default=100, alias="endRow")
    row_group_cols: Optional[list[Any]] = Field(default=UNSET, alias="rowGroupCols")
    value_cols: Optional[list[Any]] = Field(default=UNSET, alias="valueCols")
    group_keys: Optional[list[str]] = Field(default=UNSET, alias="groupKeys")
    filter_model: Optional[Any] = Field(default=UNSET, alias="filterModel")
    sort_model: Optional[list[Any]] = Field(default=UNSET, alias="sortModel")


class SsrmRequestDict(TypedDict):
    start_row: NotRequired[int]
    end_row: NotRequired[int]
    row_group_cols: NotRequired[list[Any]]
    value_cols: NotRequired[list[Any]]
    group_keys: NotRequired[list[str]]
    filter_model: NotRequired[Any]
    sort_model: NotRequired[list[Any]]
