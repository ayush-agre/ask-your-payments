<!-- Generated file — do not edit; regenerated with the SDK. -->

# FinancialStudioGrid — operations

Accessor: `client.financial_studio_grid` · Source: `ask_your_payments_consolidated_platform_api/apis/financial_studio_grid.py` · 3 operations

Each `###` block is one operation and assumes `sdk-map.md` is loaded: blocks omit what its invariants table covers and are otherwise self-contained, so chunk at block level. Signatures are the sync parsed spelling; the async and raw spellings take the same parameters (see sdk-map.md). **Type sources** names the module declaring each type an operation mentions, so resolving a body, return or error payload is a lookup rather than a search; the runtime types `RawError` and `ApiResult` are excluded.

### client.financial_studio_grid.get_evidence_detail_api_v1_evidence_match_id_get

- **Route**: `GET /api/v1/evidence/{match_id}`
- **Signature**: `def get_evidence_detail_api_v1_evidence_match_id_get(match_id: str, *, request_options: RequestOptionsOrDict | None = None)`
  - required, positional: `match_id`
- **Params**: `match_id` — path
- **Returns (parsed)**: `Any`
- **Returns (raw)**: `ApiResult[Any, GetEvidenceDetailApiV1EvidenceMatchIdGetErrorBody]`
- **Error**: `GetEvidenceDetailApiV1EvidenceMatchIdGetErrorBody` — **Case A (typed)**
- **Error arms**: `HttpValidationError` [422] · `RawError` [anything unmapped]

| Type | Source |
| --- | --- |
| `GetEvidenceDetailApiV1EvidenceMatchIdGetErrorBody` | `ask_your_payments_consolidated_platform_api/errors/get_evidence_detail_api_v1_evidence_match_id_get_error.py` |
| `HttpValidationError` | `ask_your_payments_consolidated_platform_api/models/http_validation_error.py` |

### client.financial_studio_grid.get_grid_rows_api_v1_grid_rows_post

- **Route**: `POST /api/v1/grid/rows`
- **Signature**: `def get_grid_rows_api_v1_grid_rows_post(body: SsrmRequest | SsrmRequestDict, *, request_options: RequestOptionsOrDict | None = None)`
  - required, positional: `body`
- **Params**: `body` — JSON body
- **Returns (parsed)**: `Any`
- **Returns (raw)**: `ApiResult[Any, GetGridRowsApiV1GridRowsPostErrorBody]`
- **Error**: `GetGridRowsApiV1GridRowsPostErrorBody` — **Case A (typed)**
- **Error arms**: `HttpValidationError` [422] · `RawError` [anything unmapped]

| Type | Source |
| --- | --- |
| `SsrmRequest` | `ask_your_payments_consolidated_platform_api/models/ssrm_request.py` |
| `SsrmRequestDict` | `ask_your_payments_consolidated_platform_api/models/ssrm_request.py` |
| `GetGridRowsApiV1GridRowsPostErrorBody` | `ask_your_payments_consolidated_platform_api/errors/get_grid_rows_api_v1_grid_rows_post_error.py` |
| `HttpValidationError` | `ask_your_payments_consolidated_platform_api/models/http_validation_error.py` |

### client.financial_studio_grid.override_match_api_v1_matches_match_id_override_patch

- **Route**: `PATCH /api/v1/matches/{match_id}/override`
- **Signature**: `def override_match_api_v1_matches_match_id_override_patch(match_id: str, body: OverrideRequestPayload | OverrideRequestPayloadDict, *, request_options: RequestOptionsOrDict | None = None)`
  - required, positional: `match_id`, `body`
- **Params**: `match_id` — path · `body` — JSON body
- **Returns (parsed)**: `Any`
- **Returns (raw)**: `ApiResult[Any, OverrideMatchApiV1MatchesMatchIdOverridePatchErrorBody]`
- **Error**: `OverrideMatchApiV1MatchesMatchIdOverridePatchErrorBody` — **Case A (typed)**
- **Error arms**: `HttpValidationError` [422] · `RawError` [anything unmapped]

| Type | Source |
| --- | --- |
| `OverrideRequestPayload` | `ask_your_payments_consolidated_platform_api/models/override_request_payload.py` |
| `OverrideRequestPayloadDict` | `ask_your_payments_consolidated_platform_api/models/override_request_payload.py` |
| `OverrideMatchApiV1MatchesMatchIdOverridePatchErrorBody` | `ask_your_payments_consolidated_platform_api/errors/override_match_api_v1_matches_match_id_override_patch_error.py` |
| `HttpValidationError` | `ask_your_payments_consolidated_platform_api/models/http_validation_error.py` |

