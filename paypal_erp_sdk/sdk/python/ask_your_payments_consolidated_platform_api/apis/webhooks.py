from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from ..core import (
    ApiResult,
    AsyncRawClient,
    BaseRawResponse,
    RawClient,
    RequestOptionsOrDict,
    async_json_decoder,
    json_body,
    json_decoder,
    param,
    unwrap,
)
from ..errors.paypal_webhook_handler_webhook_paypal_post_error import (
    PaypalWebhookHandlerWebhookPaypalPostErrorBody,
    paypal_webhook_handler_webhook_paypal_post_error_mapper,
)
from ..models.pay_pal_webhook_payload import PayPalWebhookPayload, PayPalWebhookPayloadDict
from ..server.server import Server


class Webhooks:
    def __init__(self, client: RawClient, server: Server) -> None:
        self._with_raw_response = WebhooksWithRawResponse(client, server)

    def paypal_webhook_handler_webhook_paypal_post(
        self,
        body: PayPalWebhookPayload | PayPalWebhookPayloadDict,
        *,
        request_options: RequestOptionsOrDict | None = None,
    ) -> Any:
        """Simulates receiving a PayPal webhook:
          1. Dedupes and records event into BronzeEvent table.
          2. Locates matching Gold reconciliation record by paypal_transaction_id or reference_invoice_id.
          3. Updates match_status to 'matched'.
          4. Broadcasts a 'WEBHOOK_ACK' event to all connected AG Grid WebSockets
             for instant, frame-safe row flashing and status update.

        Args:
            body: The request body.
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            Successful Response

        Raises:
            ApiError: Validation Error ``error`` is ``HttpValidationError | RawError``."""
        return unwrap(
            self._with_raw_response.paypal_webhook_handler_webhook_paypal_post(body, request_options=request_options)
        )

    @property
    def with_raw_response(self) -> WebhooksWithRawResponse:
        return self._with_raw_response


class AsyncWebhooks:
    def __init__(self, client: AsyncRawClient, server: Server) -> None:
        self._with_raw_response = AsyncWebhooksWithRawResponse(client, server)

    async def paypal_webhook_handler_webhook_paypal_post(
        self,
        body: PayPalWebhookPayload | PayPalWebhookPayloadDict,
        *,
        request_options: RequestOptionsOrDict | None = None,
    ) -> Any:
        """Simulates receiving a PayPal webhook:
          1. Dedupes and records event into BronzeEvent table.
          2. Locates matching Gold reconciliation record by paypal_transaction_id or reference_invoice_id.
          3. Updates match_status to 'matched'.
          4. Broadcasts a 'WEBHOOK_ACK' event to all connected AG Grid WebSockets
             for instant, frame-safe row flashing and status update.

        Args:
            body: The request body.
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            Successful Response

        Raises:
            ApiError: Validation Error ``error`` is ``HttpValidationError | RawError``."""
        return unwrap(
            await self._with_raw_response.paypal_webhook_handler_webhook_paypal_post(
                body, request_options=request_options
            ),
        )

    @property
    def with_raw_response(self) -> AsyncWebhooksWithRawResponse:
        return self._with_raw_response


class WebhooksWithRawResponse(BaseRawResponse[RawClient, Server]):
    def paypal_webhook_handler_webhook_paypal_post(
        self,
        body: PayPalWebhookPayload | PayPalWebhookPayloadDict,
        *,
        request_options: RequestOptionsOrDict | None = None,
    ) -> ApiResult[Any, PaypalWebhookHandlerWebhookPaypalPostErrorBody]:
        """Simulates receiving a PayPal webhook:
          1. Dedupes and records event into BronzeEvent table.
          2. Locates matching Gold reconciliation record by paypal_transaction_id or reference_invoice_id.
          3. Updates match_status to 'matched'.
          4. Broadcasts a 'WEBHOOK_ACK' event to all connected AG Grid WebSockets
             for instant, frame-safe row flashing and status update.

        Args:
            body: The request body.
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            An ``ApiResult`` holding the deserialized response or the error body."""
        return self._client.execute(
            http_method="POST",
            url_template=self._server.default("/webhook/paypal"),
            headers=[param[UUID]("Idempotency-Key", uuid4())],
            body=json_body[PayPalWebhookPayload | PayPalWebhookPayloadDict](body),
            decoder=json_decoder[Any],
            error_mapper=paypal_webhook_handler_webhook_paypal_post_error_mapper,
            request_options=request_options,
        )


class AsyncWebhooksWithRawResponse(BaseRawResponse[AsyncRawClient, Server]):
    async def paypal_webhook_handler_webhook_paypal_post(
        self,
        body: PayPalWebhookPayload | PayPalWebhookPayloadDict,
        *,
        request_options: RequestOptionsOrDict | None = None,
    ) -> ApiResult[Any, PaypalWebhookHandlerWebhookPaypalPostErrorBody]:
        """Simulates receiving a PayPal webhook:
          1. Dedupes and records event into BronzeEvent table.
          2. Locates matching Gold reconciliation record by paypal_transaction_id or reference_invoice_id.
          3. Updates match_status to 'matched'.
          4. Broadcasts a 'WEBHOOK_ACK' event to all connected AG Grid WebSockets
             for instant, frame-safe row flashing and status update.

        Args:
            body: The request body.
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            An ``ApiResult`` holding the deserialized response or the error body."""
        return await self._client.execute(
            http_method="POST",
            url_template=self._server.default("/webhook/paypal"),
            headers=[param[UUID]("Idempotency-Key", uuid4())],
            body=json_body[PayPalWebhookPayload | PayPalWebhookPayloadDict](body),
            decoder=async_json_decoder[Any],
            error_mapper=paypal_webhook_handler_webhook_paypal_post_error_mapper,
            request_options=request_options,
        )
