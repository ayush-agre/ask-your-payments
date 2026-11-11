from __future__ import annotations

from typing import Any

from typing_extensions import TypedDict

from ..core import SdkBaseModel


class InvestigationResultRow(SdkBaseModel):
    """A single row in the investigation result set."""

    data: Any
    """Column name → value mapping for this row."""


class InvestigationResultRowDict(TypedDict):
    data: Any
