from __future__ import annotations

from dataclasses import dataclass
from typing import Final, TypeAlias

from ..core import ErrorMapper, RawError, decode_json
from ..models.http_validation_error import HttpValidationError

PaypalWebhookHandlerWebhookPaypalPostErrorBody: TypeAlias = HttpValidationError | RawError


@dataclass(frozen=True, slots=True)
class _PaypalWebhookHandlerWebhookPaypalPostError:
    def map(self, status_code: int, content: bytes) -> PaypalWebhookHandlerWebhookPaypalPostErrorBody:
        match status_code:
            case 422:
                return decode_json[HttpValidationError](content)
            case _:
                return RawError(status_code, content)


paypal_webhook_handler_webhook_paypal_post_error_mapper: Final[
    ErrorMapper[PaypalWebhookHandlerWebhookPaypalPostErrorBody]
] = _PaypalWebhookHandlerWebhookPaypalPostError()
