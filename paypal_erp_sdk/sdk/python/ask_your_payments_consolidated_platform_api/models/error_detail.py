from __future__ import annotations

from typing_extensions import TypedDict

from ..core import SdkBaseModel


class ErrorDetail(SdkBaseModel):
    field: str
    issue: str


class ErrorDetailDict(TypedDict):
    field: str
    issue: str
