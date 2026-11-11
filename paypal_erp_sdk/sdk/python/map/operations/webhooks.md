<!-- Generated file — do not edit; regenerated with the SDK. -->

# Webhooks — operations

Accessor: `client.webhooks` · Source: `ask_your_payments_consolidated_platform_api/apis/webhooks.py` · 1 operation

Each `###` block is one operation and assumes `sdk-map.md` is loaded: blocks omit what its invariants table covers and are otherwise self-contained, so chunk at block level. Signatures are the sync parsed spelling; the async and raw spellings take the same parameters (see sdk-map.md). **Type sources** names the module declaring each type an operation mentions, so resolving a body, return or error payload is a lookup rather than a search; the runtime types `RawError` and `ApiResult` are excluded.

### client.webhooks.paypal_webhook_handler_webhook_paypal_post

- **Route**: `POST /webhook/paypal`
- **Signature**: `def paypal_webhook_handler_webhook_paypal_post(body: PayPalWebhookPayload | PayPalWebhookPayloadDict, *, request_options: RequestOptionsOrDict | None = None)`
  - required, positional: `body`
- **Params**: `body` — JSON body
- **Returns (parsed)**: `Any`
- **Returns (raw)**: `ApiResult[Any, PaypalWebhookHandlerWebhookPaypalPostErrorBody]`
- **Error**: `PaypalWebhookHandlerWebhookPaypalPostErrorBody` — **Case A (typed)**
- **Error arms**: `HttpValidationError` [422] · `RawError` [anything unmapped]

| Type | Source |
| --- | --- |
| `PayPalWebhookPayload` | `ask_your_payments_consolidated_platform_api/models/pay_pal_webhook_payload.py` |
| `PayPalWebhookPayloadDict` | `ask_your_payments_consolidated_platform_api/models/pay_pal_webhook_payload.py` |
| `PaypalWebhookHandlerWebhookPaypalPostErrorBody` | `ask_your_payments_consolidated_platform_api/errors/paypal_webhook_handler_webhook_paypal_post_error.py` |
| `HttpValidationError` | `ask_your_payments_consolidated_platform_api/models/http_validation_error.py` |

