from __future__ import annotations

from typing_extensions import NotRequired, TypedDict

from ..core import UNSET, Optional, SdkBaseModel
from .enums.match_status import MatchStatusOrStr


class OverrideRequestPayload(SdkBaseModel):
    """FinOps controller cell override request."""

    override_status: MatchStatusOrStr
    """Lifecycle state of a match."""

    review_notes: str
    action: Optional[str] = UNSET
    four_eyes_proposer: str = "finops_analyst"


class OverrideRequestPayloadDict(TypedDict):
    override_status: MatchStatusOrStr
    review_notes: str
    action: NotRequired[str]
    four_eyes_proposer: NotRequired[str]
