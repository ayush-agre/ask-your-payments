<!-- Generated file — do not edit; regenerated with the SDK. -->

# System — operations

Accessor: `client.system` · Source: `ask_your_payments_consolidated_platform_api/apis/system.py` · 2 operations

Each `###` block is one operation and assumes `sdk-map.md` is loaded: blocks omit what its invariants table covers and are otherwise self-contained, so chunk at block level. Signatures are the sync parsed spelling; the async and raw spellings take the same parameters (see sdk-map.md). **Type sources** names the module declaring each type an operation mentions, so resolving a body, return or error payload is a lookup rather than a search; the runtime types `RawError` and `ApiResult` are excluded, and an operation with no table mentions nothing but builtins and those.

### client.system.health_check_health_get

- **Route**: `GET /health`
- **Signature**: `def health_check_health_get(*, request_options: RequestOptionsOrDict | None = None)`
- **Returns (parsed)**: `dict[str, str]`
- **Returns (raw)**: `ApiResult[dict[str, str], RawError]`
- **Error**: `RawError` — **Case B**

### client.system.health_check_healthz_get

- **Route**: `GET /healthz`
- **Signature**: `def health_check_healthz_get(*, request_options: RequestOptionsOrDict | None = None)`
- **Returns (parsed)**: `dict[str, str]`
- **Returns (raw)**: `ApiResult[dict[str, str], RawError]`
- **Error**: `RawError` — **Case B**

