from __future__ import annotations

from typing_extensions import TypedDict

from ..core import SdkBaseModel


class Pagination(SdkBaseModel):
    page: int
    page_size: int
    total_records: int
    total_pages: int


class PaginationDict(TypedDict):
    page: int
    page_size: int
    total_records: int
    total_pages: int
