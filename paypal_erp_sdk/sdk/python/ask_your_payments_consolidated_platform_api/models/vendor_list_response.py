from __future__ import annotations

from typing_extensions import TypedDict

from ..core import SdkBaseModel
from .pagination import Pagination, PaginationDict
from .vendor import Vendor, VendorDict


class VendorListResponse(SdkBaseModel):
    data: list[Vendor]
    pagination: Pagination


class VendorListResponseDict(TypedDict):
    data: list[VendorDict]
    pagination: PaginationDict
