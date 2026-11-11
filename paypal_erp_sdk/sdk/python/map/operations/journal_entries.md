<!-- Generated file — do not edit; regenerated with the SDK. -->

# JournalEntries — operations

Accessor: `client.journal_entries` · Source: `ask_your_payments_consolidated_platform_api/apis/journal_entries.py` · 1 operation

Each `###` block is one operation and assumes `sdk-map.md` is loaded: blocks omit what its invariants table covers and are otherwise self-contained, so chunk at block level. Signatures are the sync parsed spelling; the async and raw spellings take the same parameters (see sdk-map.md). **Type sources** names the module declaring each type an operation mentions, so resolving a body, return or error payload is a lookup rather than a search; the runtime types `RawError` and `ApiResult` are excluded.

### client.journal_entries.create_journal_entry

- **Route**: `POST /api/journal-entries`
- **Signature**: `def create_journal_entry(body: JournalEntryRequest | JournalEntryRequestDict, *, idempotency_key: str | None = None, request_options: RequestOptionsOrDict | None = None)`
  - required, positional: `body`
- **Params**: `idempotency_key` — header `Idempotency-Key` · `body` — JSON body
- **Returns (parsed)**: `JournalEntryResponse`
- **Returns (raw)**: `ApiResult[JournalEntryResponse, CreateJournalEntryErrorBody]`
- **Error**: `CreateJournalEntryErrorBody` — **Case A (typed)**
- **Error arms**: `Error` [400, 401, 403, 409, 422, 429, 500] · `RawError` [anything unmapped]

| Type | Source |
| --- | --- |
| `JournalEntryRequest` | `ask_your_payments_consolidated_platform_api/models/journal_entry_request.py` |
| `JournalEntryRequestDict` | `ask_your_payments_consolidated_platform_api/models/journal_entry_request.py` |
| `JournalEntryResponse` | `ask_your_payments_consolidated_platform_api/models/journal_entry_response.py` |
| `CreateJournalEntryErrorBody` | `ask_your_payments_consolidated_platform_api/errors/create_journal_entry_error.py` |
| `Error` | `ask_your_payments_consolidated_platform_api/models/error.py` |

