from __future__ import annotations

from typing import Any

from typing_extensions import NotRequired, TypedDict

from ..core import UNSET, Optional, SdkBaseModel


class PayPalWebhookPayload(SdkBaseModel):
    """Incoming PayPal Webhook JSON simulation model."""

    id: str
    """PayPal Webhook Event ID"""

    event_type: str
    """E.g. PAYMENT.CAPTURE.COMPLETED, CHECKOUT.ORDER.APPROVED"""

    resource_type: str = "capture"
    """Resource type"""

    summary: Optional[str] = UNSET
    """Event summary narrative"""

    resource: Any
    """Full webhook resource payload"""


class PayPalWebhookPayloadDict(TypedDict):
    id: str
    event_type: str
    resource_type: NotRequired[str]
    summary: NotRequired[str]
    resource: Any
