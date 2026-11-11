<!-- Generated file — do not edit; regenerated with the SDK. -->

# Invoices — operations

Accessor: `client.invoices` · Source: `ask_your_payments_consolidated_platform_api/apis/invoices.py` · 1 operation

Each `###` block is one operation and assumes `sdk-map.md` is loaded: blocks omit what its invariants table covers and are otherwise self-contained, so chunk at block level. Signatures are the sync parsed spelling; the async and raw spellings take the same parameters (see sdk-map.md). **Type sources** names the module declaring each type an operation mentions, so resolving a body, return or error payload is a lookup rather than a search; the runtime types `RawError` and `ApiResult` are excluded.

### client.invoices.list_invoices

- **Route**: `GET /api/invoices`
- **Signature**: `def list_invoices(*, status: InvoiceStatusOrStr | None = None, vendor_id: str | None = None, from_date: Date | None = None, to_date: Date | None = None, page: int | None = 1, page_size: int | None = 25, request_options: RequestOptionsOrDict | None = None)`
- **Params**: `status` — query · `vendor_id` — query · `from_date` — query · `to_date` — query · `page` — query · `page_size` — query
- **Returns (parsed)**: `InvoiceListResponse`
- **Returns (raw)**: `ApiResult[InvoiceListResponse, ListInvoicesErrorBody]`
- **Error**: `ListInvoicesErrorBody` — **Case A (typed)**
- **Error arms**: `Error` [400, 401, 403, 429, 500] · `RawError` [anything unmapped]

| Type | Source |
| --- | --- |
| `InvoiceStatusOrStr` | `ask_your_payments_consolidated_platform_api/models/enums/invoice_status.py` |
| `InvoiceListResponse` | `ask_your_payments_consolidated_platform_api/models/invoice_list_response.py` |
| `ListInvoicesErrorBody` | `ask_your_payments_consolidated_platform_api/errors/list_invoices_error.py` |
| `Error` | `ask_your_payments_consolidated_platform_api/models/error.py` |

