<!-- Generated file — do not edit; regenerated with the SDK. -->

# AiInvestigation — operations

Accessor: `client.ai_investigation` · Source: `ask_your_payments_consolidated_platform_api/apis/ai_investigation.py` · 2 operations

Each `###` block is one operation and assumes `sdk-map.md` is loaded: blocks omit what its invariants table covers and are otherwise self-contained, so chunk at block level. Signatures are the sync parsed spelling; the async and raw spellings take the same parameters (see sdk-map.md). **Type sources** names the module declaring each type an operation mentions, so resolving a body, return or error payload is a lookup rather than a search; the runtime types `RawError` and `ApiResult` are excluded, and an operation with no table mentions nothing but builtins and those.

### client.ai_investigation.ai_health_api_v1_investigate_health_get

- **Route**: `GET /api/v1/investigate/health`
- **Signature**: `def ai_health_api_v1_investigate_health_get(*, request_options: RequestOptionsOrDict | None = None)`
- **Returns (parsed)**: `dict[str, str]`
- **Returns (raw)**: `ApiResult[dict[str, str], RawError]`
- **Error**: `RawError` — **Case B**

### client.ai_investigation.investigate_api_v1_investigate_post

- **Route**: `POST /api/v1/investigate/`
- **Signature**: `def investigate_api_v1_investigate_post(body: InvestigationRequest | InvestigationRequestDict, *, request_options: RequestOptionsOrDict | None = None)`
  - required, positional: `body`
- **Params**: `body` — JSON body
- **Returns (parsed)**: `InvestigationResponse`
- **Returns (raw)**: `ApiResult[InvestigationResponse, InvestigateApiV1InvestigatePostErrorBody]`
- **Error**: `InvestigateApiV1InvestigatePostErrorBody` — **Case A (typed)**
- **Error arms**: `RawError` [422, 502, anything unmapped]

| Type | Source |
| --- | --- |
| `InvestigationRequest` | `ask_your_payments_consolidated_platform_api/models/investigation_request.py` |
| `InvestigationRequestDict` | `ask_your_payments_consolidated_platform_api/models/investigation_request.py` |
| `InvestigationResponse` | `ask_your_payments_consolidated_platform_api/models/investigation_response.py` |
| `InvestigateApiV1InvestigatePostErrorBody` | `ask_your_payments_consolidated_platform_api/errors/investigate_api_v1_investigate_post_error.py` |

