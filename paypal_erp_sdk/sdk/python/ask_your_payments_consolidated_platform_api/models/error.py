from __future__ import annotations

from typing_extensions import NotRequired, TypedDict

from ..core import UNSET, Optional, SdkBaseModel
from .error_detail import ErrorDetail, ErrorDetailDict


class Error(SdkBaseModel):
    code: str
    message: str
    request_id: str
    details: Optional[list[ErrorDetail]] = UNSET


class ErrorDict(TypedDict):
    code: str
    message: str
    request_id: str
    details: NotRequired[list[ErrorDetailDict]]
