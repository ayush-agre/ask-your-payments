from __future__ import annotations

from typing_extensions import NotRequired, TypedDict

from ..core import UNSET, Optional, SdkBaseModel


class InvestigationRequest(SdkBaseModel):
    """Inbound request from the FinOps manager."""

    query: str
    """Natural language investigation query."""

    tenant_id: Optional[str] = UNSET
    """Tenant context for multi-tenant isolation."""

    requested_by: str = "anonymous"
    """Authenticated user initiating the investigation."""

    max_results: int = 100
    """Maximum rows the user wants returned."""


class InvestigationRequestDict(TypedDict):
    query: str
    tenant_id: NotRequired[str]
    requested_by: NotRequired[str]
    max_results: NotRequired[int]
