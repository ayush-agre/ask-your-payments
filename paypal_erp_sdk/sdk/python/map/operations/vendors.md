<!-- Generated file — do not edit; regenerated with the SDK. -->

# Vendors — operations

Accessor: `client.vendors` · Source: `ask_your_payments_consolidated_platform_api/apis/vendors.py` · 1 operation

Each `###` block is one operation and assumes `sdk-map.md` is loaded: blocks omit what its invariants table covers and are otherwise self-contained, so chunk at block level. Signatures are the sync parsed spelling; the async and raw spellings take the same parameters (see sdk-map.md). **Type sources** names the module declaring each type an operation mentions, so resolving a body, return or error payload is a lookup rather than a search; the runtime types `RawError` and `ApiResult` are excluded.

### client.vendors.list_vendors

- **Route**: `GET /api/vendors`
- **Signature**: `def list_vendors(*, active: bool | None = None, search: str | None = None, page: int | None = 1, page_size: int | None = 25, request_options: RequestOptionsOrDict | None = None)`
- **Params**: `active` — query · `search` — query · `page` — query · `page_size` — query
- **Returns (parsed)**: `VendorListResponse`
- **Returns (raw)**: `ApiResult[VendorListResponse, ListVendorsErrorBody]`
- **Error**: `ListVendorsErrorBody` — **Case A (typed)**
- **Error arms**: `Error` [400, 401, 403, 429, 500] · `RawError` [anything unmapped]

| Type | Source |
| --- | --- |
| `VendorListResponse` | `ask_your_payments_consolidated_platform_api/models/vendor_list_response.py` |
| `ListVendorsErrorBody` | `ask_your_payments_consolidated_platform_api/errors/list_vendors_error.py` |
| `Error` | `ask_your_payments_consolidated_platform_api/models/error.py` |

