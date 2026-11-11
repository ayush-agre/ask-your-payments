# Reference

**Parsed** endpoints return the typed payload and raise `ApiError` on a documented non-2xx. For the raw endpoints, see [Raw API Reference](raw-api-reference.md).

> Source: [AskYourPaymentsConsolidatedPlatformApiClient](ask_your_payments_consolidated_platform_api/client.py)

## AiInvestigation

> Source: [AiInvestigation](ask_your_payments_consolidated_platform_api/apis/ai_investigation.py)

<details>
<summary><code>def ai_health_api_v1_investigate_health_get(*, request_options: RequestOptionsOrDict | None = None) -> dict[str, str]</code></summary>

<dl>
<dd>

### Description

<dl>
<dd>

Verify the AI investigation router is operational.

</dd>
</dl>

### Usage

<dl>
<dd>

**Sync**

```python
try:
    response = client.ai_investigation.ai_health_api_v1_investigate_health_get()
    # TODO: Handle 'response' of type dict[str, str]
except ApiError as e:
    ...  # TODO: Handle 'e.error' of type RawError
```

**Async**

```python
try:
    response = await async_client.ai_investigation.ai_health_api_v1_investigate_health_get()
    # TODO: Handle 'response' of type dict[str, str]
except ApiError as e:
    ...  # TODO: Handle 'e.error' of type RawError
```

</dd>
</dl>

### Parameters

<dl>
<dd>

| Name | Type | Description |
| --- | --- | --- |
| <code>request_options</code> | <code>[RequestOptionsOrDict](ask_your_payments_consolidated_platform_api/core/request_options.py) \| None</code> | Per-call overrides for this one request, such as a timeout, extra headers, or its retry count and statuses. |

</dd>
</dl>

### Response

<dl>
<dd>

**OnSuccess**: <code>dict&#91;str, str&#93;</code> -- Successful Response

**OnError**: <code>[ApiError](ask_your_payments_consolidated_platform_api/core/exceptions.py)&#91;[RawError](ask_your_payments_consolidated_platform_api/core/results.py)&#93;</code>

</dd>
</dl>

</dd>
</dl>

</details>

<details>
<summary><code>def investigate_api_v1_investigate_post(body: InvestigationRequest | InvestigationRequestDict, *, request_options: RequestOptionsOrDict | None = None) -> InvestigationResponse</code></summary>

<dl>
<dd>

### Description

<dl>
<dd>

Accepts a natural language query from a FinOps manager, applies PII minimisation, sends the sanitised query to Gemini 2.5 Flash for intent extraction, and compiles the result into allowlisted parameterised SQL against the Silver/Gold operational records.

</dd>
</dl>

### Usage

<dl>
<dd>

**Sync**

```python
try:
    response = client.ai_investigation.investigate_api_v1_investigate_post(
        InvestigationRequest(query="some example string")
    )
    # TODO: Handle 'response' of type InvestigationResponse
except ApiError as e:
    ...  # TODO: Handle 'e.error' of type InvestigateApiV1InvestigatePostErrorBody
```

**Async**

```python
try:
    response = await async_client.ai_investigation.investigate_api_v1_investigate_post(
        InvestigationRequest(query="some example string")
    )
    # TODO: Handle 'response' of type InvestigationResponse
except ApiError as e:
    ...  # TODO: Handle 'e.error' of type InvestigateApiV1InvestigatePostErrorBody
```

</dd>
</dl>

### Parameters

<dl>
<dd>

| Name | Type | Description |
| --- | --- | --- |
| <code>body</code> | <code>[InvestigationRequest](ask_your_payments_consolidated_platform_api/models/investigation_request.py) \| [InvestigationRequestDict](ask_your_payments_consolidated_platform_api/models/investigation_request.py)</code> | The request body. |
| <code>request_options</code> | <code>[RequestOptionsOrDict](ask_your_payments_consolidated_platform_api/core/request_options.py) \| None</code> | Per-call overrides for this one request, such as a timeout, extra headers, or its retry count and statuses. |

</dd>
</dl>

### Response

<dl>
<dd>

**OnSuccess**: <code>[InvestigationResponse](ask_your_payments_consolidated_platform_api/models/investigation_response.py)</code> -- Successful Response

**OnError**: <code>[ApiError](ask_your_payments_consolidated_platform_api/core/exceptions.py)&#91;[InvestigateApiV1InvestigatePostErrorBody](ask_your_payments_consolidated_platform_api/errors/investigate_api_v1_investigate_post_error.py)&#93;</code>

Mapped in first-match order -- an earlier row wins over a later range that also covers the status:

| Status | `error` is |
| --- | --- |
| 422, 502 | <code>[RawError](ask_your_payments_consolidated_platform_api/core/results.py)</code> |
| anything unmapped | <code>[RawError](ask_your_payments_consolidated_platform_api/core/results.py)</code> |

</dd>
</dl>

</dd>
</dl>

</details>

## FinancialStudioGrid

> Source: [FinancialStudioGrid](ask_your_payments_consolidated_platform_api/apis/financial_studio_grid.py)

<details>
<summary><code>def get_evidence_detail_api_v1_evidence_match_id_get(match_id: str, *, request_options: RequestOptionsOrDict | None = None) -> Any</code></summary>

<dl>
<dd>

### Description

<dl>
<dd>

Lazy-loads full audit evidence when a FinOps manager expands a row.
Returns ERP Invoice vs. PayPal settlement comparison, anomaly flags,
and associated double-entry journal lines.

</dd>
</dl>

### Usage

<dl>
<dd>

**Sync**

```python
try:
    response = client.financial_studio_grid.get_evidence_detail_api_v1_evidence_match_id_get("some example string")
    # TODO: Handle 'response' of type Any
except ApiError as e:
    ...  # TODO: Handle 'e.error' of type GetEvidenceDetailApiV1EvidenceMatchIdGetErrorBody
```

**Async**

```python
try:
    response = await async_client.financial_studio_grid.get_evidence_detail_api_v1_evidence_match_id_get(
        "some example string"
    )
    # TODO: Handle 'response' of type Any
except ApiError as e:
    ...  # TODO: Handle 'e.error' of type GetEvidenceDetailApiV1EvidenceMatchIdGetErrorBody
```

</dd>
</dl>

### Parameters

<dl>
<dd>

| Name | Type | Description |
| --- | --- | --- |
| <code>match_id</code> | <code>str</code> | Value sent with the request. |
| <code>request_options</code> | <code>[RequestOptionsOrDict](ask_your_payments_consolidated_platform_api/core/request_options.py) \| None</code> | Per-call overrides for this one request, such as a timeout, extra headers, or its retry count and statuses. |

</dd>
</dl>

### Response

<dl>
<dd>

**OnSuccess**: <code>Any</code> -- Successful Response

**OnError**: <code>[ApiError](ask_your_payments_consolidated_platform_api/core/exceptions.py)&#91;[GetEvidenceDetailApiV1EvidenceMatchIdGetErrorBody](ask_your_payments_consolidated_platform_api/errors/get_evidence_detail_api_v1_evidence_match_id_get_error.py)&#93;</code>

Mapped in first-match order -- an earlier row wins over a later range that also covers the status:

| Status | `error` is |
| --- | --- |
| 422 | <code>[HttpValidationError](ask_your_payments_consolidated_platform_api/models/http_validation_error.py)</code> |
| anything unmapped | <code>[RawError](ask_your_payments_consolidated_platform_api/core/results.py)</code> |

</dd>
</dl>

</dd>
</dl>

</details>

<details>
<summary><code>def get_grid_rows_api_v1_grid_rows_post(body: SsrmRequest | SsrmRequestDict, *, request_options: RequestOptionsOrDict | None = None) -> Any</code></summary>

<dl>
<dd>

### Description

<dl>
<dd>

Serves row data directly to AG Grid Server-Side Row Model (SSRM).
Supports pagination, multi-column sorting, and joins Gold reconciliation
matches with Silver PayPal settlements and Silver ERP invoices.

</dd>
</dl>

### Usage

<dl>
<dd>

**Sync**

```python
try:
    response = client.financial_studio_grid.get_grid_rows_api_v1_grid_rows_post(SsrmRequest())
    # TODO: Handle 'response' of type Any
except ApiError as e:
    ...  # TODO: Handle 'e.error' of type GetGridRowsApiV1GridRowsPostErrorBody
```

**Async**

```python
try:
    response = await async_client.financial_studio_grid.get_grid_rows_api_v1_grid_rows_post(SsrmRequest())
    # TODO: Handle 'response' of type Any
except ApiError as e:
    ...  # TODO: Handle 'e.error' of type GetGridRowsApiV1GridRowsPostErrorBody
```

</dd>
</dl>

### Parameters

<dl>
<dd>

| Name | Type | Description |
| --- | --- | --- |
| <code>body</code> | <code>[SsrmRequest](ask_your_payments_consolidated_platform_api/models/ssrm_request.py) \| [SsrmRequestDict](ask_your_payments_consolidated_platform_api/models/ssrm_request.py)</code> | The request body. |
| <code>request_options</code> | <code>[RequestOptionsOrDict](ask_your_payments_consolidated_platform_api/core/request_options.py) \| None</code> | Per-call overrides for this one request, such as a timeout, extra headers, or its retry count and statuses. |

</dd>
</dl>

### Response

<dl>
<dd>

**OnSuccess**: <code>Any</code> -- Successful Response

**OnError**: <code>[ApiError](ask_your_payments_consolidated_platform_api/core/exceptions.py)&#91;[GetGridRowsApiV1GridRowsPostErrorBody](ask_your_payments_consolidated_platform_api/errors/get_grid_rows_api_v1_grid_rows_post_error.py)&#93;</code>

Mapped in first-match order -- an earlier row wins over a later range that also covers the status:

| Status | `error` is |
| --- | --- |
| 422 | <code>[HttpValidationError](ask_your_payments_consolidated_platform_api/models/http_validation_error.py)</code> |
| anything unmapped | <code>[RawError](ask_your_payments_consolidated_platform_api/core/results.py)</code> |

</dd>
</dl>

</dd>
</dl>

</details>

<details>
<summary><code>def override_match_api_v1_matches_match_id_override_patch(match_id: str, body: OverrideRequestPayload | OverrideRequestPayloadDict, *, request_options: RequestOptionsOrDict | None = None) -> Any</code></summary>

<dl>
<dd>

### Description

<dl>
<dd>

Processes manual FinOps controller overrides inside an AG Grid cell.
Stages an operation subject to Four-Eyes human verification and broadcasts
the updated match status to all connected WebSockets.

</dd>
</dl>

### Usage

<dl>
<dd>

**Sync**

```python
try:
    response = client.financial_studio_grid.override_match_api_v1_matches_match_id_override_patch(
        "some example string",
        OverrideRequestPayload(override_status=MatchStatus.MATCHED, review_notes="some example string"),
    )
    # TODO: Handle 'response' of type Any
except ApiError as e:
    ...  # TODO: Handle 'e.error' of type OverrideMatchApiV1MatchesMatchIdOverridePatchErrorBody
```

**Async**

```python
try:
    response = await async_client.financial_studio_grid.override_match_api_v1_matches_match_id_override_patch(
        "some example string",
        OverrideRequestPayload(override_status=MatchStatus.MATCHED, review_notes="some example string"),
    )
    # TODO: Handle 'response' of type Any
except ApiError as e:
    ...  # TODO: Handle 'e.error' of type OverrideMatchApiV1MatchesMatchIdOverridePatchErrorBody
```

</dd>
</dl>

### Parameters

<dl>
<dd>

| Name | Type | Description |
| --- | --- | --- |
| <code>match_id</code> | <code>str</code> | Value sent with the request. |
| <code>body</code> | <code>[OverrideRequestPayload](ask_your_payments_consolidated_platform_api/models/override_request_payload.py) \| [OverrideRequestPayloadDict](ask_your_payments_consolidated_platform_api/models/override_request_payload.py)</code> | The request body. |
| <code>request_options</code> | <code>[RequestOptionsOrDict](ask_your_payments_consolidated_platform_api/core/request_options.py) \| None</code> | Per-call overrides for this one request, such as a timeout, extra headers, or its retry count and statuses. |

</dd>
</dl>

### Response

<dl>
<dd>

**OnSuccess**: <code>Any</code> -- Successful Response

**OnError**: <code>[ApiError](ask_your_payments_consolidated_platform_api/core/exceptions.py)&#91;[OverrideMatchApiV1MatchesMatchIdOverridePatchErrorBody](ask_your_payments_consolidated_platform_api/errors/override_match_api_v1_matches_match_id_override_patch_error.py)&#93;</code>

Mapped in first-match order -- an earlier row wins over a later range that also covers the status:

| Status | `error` is |
| --- | --- |
| 422 | <code>[HttpValidationError](ask_your_payments_consolidated_platform_api/models/http_validation_error.py)</code> |
| anything unmapped | <code>[RawError](ask_your_payments_consolidated_platform_api/core/results.py)</code> |

</dd>
</dl>

</dd>
</dl>

</details>

## Invoices

> Source: [Invoices](ask_your_payments_consolidated_platform_api/apis/invoices.py)

<details>
<summary><code>def list_invoices(*, status: InvoiceStatusOrStr | None = None, vendor_id: str | None = None, from_date: Date | None = None, to_date: Date | None = None, page: int | None = 1, page_size: int | None = 25, request_options: RequestOptionsOrDict | None = None) -> InvoiceListResponse</code></summary>

<dl>
<dd>

### Description

<dl>
<dd>

Returns a paginated list of AP invoices, optionally filtered by status, vendor, or date range.

</dd>
</dl>

### Usage

<dl>
<dd>

**Sync**

```python
try:
    response = client.invoices.list_invoices(
        vendor_id="VND-100234", from_date=date(2026, 10, 1), to_date=date(2026, 10, 31)
    )
    # TODO: Handle 'response' of type InvoiceListResponse
except ApiError as e:
    ...  # TODO: Handle 'e.error' of type ListInvoicesErrorBody
```

**Async**

```python
try:
    response = await async_client.invoices.list_invoices(
        vendor_id="VND-100234", from_date=date(2026, 10, 1), to_date=date(2026, 10, 31)
    )
    # TODO: Handle 'response' of type InvoiceListResponse
except ApiError as e:
    ...  # TODO: Handle 'e.error' of type ListInvoicesErrorBody
```

</dd>
</dl>

### Parameters

<dl>
<dd>

| Name | Type | Description |
| --- | --- | --- |
| <code>status</code> | <code>[InvoiceStatusOrStr](ask_your_payments_consolidated_platform_api/models/enums/invoice_status.py) \| None</code> | Filter invoices by status.<br>**Default**: <code>None</code> |
| <code>vendor_id</code> | <code>str \| None</code> | Filter invoices by vendor identifier.<br>**Default**: <code>None</code> |
| <code>from_date</code> | <code>Date \| None</code> | Return invoices dated on or after this date (YYYY-MM-DD).<br>**Default**: <code>None</code> |
| <code>to_date</code> | <code>Date \| None</code> | Return invoices dated on or before this date (YYYY-MM-DD).<br>**Default**: <code>None</code> |
| <code>page</code> | <code>int \| None</code> | 1-based page number.<br>**Default**: <code>1</code> |
| <code>page_size</code> | <code>int \| None</code> | Number of records per page.<br>**Default**: <code>25</code> |
| <code>request_options</code> | <code>[RequestOptionsOrDict](ask_your_payments_consolidated_platform_api/core/request_options.py) \| None</code> | Per-call overrides for this one request, such as a timeout, extra headers, or its retry count and statuses. |

</dd>
</dl>

### Response

<dl>
<dd>

**OnSuccess**: <code>[InvoiceListResponse](ask_your_payments_consolidated_platform_api/models/invoice_list_response.py)</code> -- A paginated list of invoices.

**OnError**: <code>[ApiError](ask_your_payments_consolidated_platform_api/core/exceptions.py)&#91;[ListInvoicesErrorBody](ask_your_payments_consolidated_platform_api/errors/list_invoices_error.py)&#93;</code>

Mapped in first-match order -- an earlier row wins over a later range that also covers the status:

| Status | `error` is |
| --- | --- |
| 400, 401, 403, 429, 500 | <code>[Error](ask_your_payments_consolidated_platform_api/models/error.py)</code> |
| anything unmapped | <code>[RawError](ask_your_payments_consolidated_platform_api/core/results.py)</code> |

</dd>
</dl>

</dd>
</dl>

</details>

## JournalEntries

> Source: [JournalEntries](ask_your_payments_consolidated_platform_api/apis/journal_entries.py)

<details>
<summary><code>def create_journal_entry(body: JournalEntryRequest | JournalEntryRequestDict, *, idempotency_key: str | None = None, request_options: RequestOptionsOrDict | None = None) -> JournalEntryResponse</code></summary>

<dl>
<dd>

### Description

<dl>
<dd>

Creates a balanced general ledger journal entry, for example to record a reconciled PayPal settlement, processing fee, or FX variance adjustment. Total debits must equal total credits.

</dd>
</dl>

### Usage

<dl>
<dd>

**Sync**

```python
try:
    response = client.journal_entries.create_journal_entry(
        JournalEntryRequest(
            posting_date=date(2026, 10, 19),
            reference_invoice_id="INV-2026-0013",
            paypal_transaction_id="7HS40927NB358164C",
            description="FX drift variance adjustment for INV-2026-0013",
            currency=CurrencyCode.INR,
            lines=[
                JournalEntryLine(
                    account_code="5900-FX-VARIANCE",
                    account_name="FX Variance Expense",
                    debit=25,
                    credit=0,
                    memo="Settlement short by INR 25.00",
                ),
                JournalEntryLine(
                    account_code="2100-AP-TRADE",
                    account_name="Accounts Payable - Trade",
                    debit=0,
                    credit=25,
                    memo="Clear residual AP balance",
                ),
            ],
        ),
        idempotency_key="recon-INV-2026-0013-20261019",
    )
    # TODO: Handle 'response' of type JournalEntryResponse
except ApiError as e:
    ...  # TODO: Handle 'e.error' of type CreateJournalEntryErrorBody
```

**Async**

```python
try:
    response = await async_client.journal_entries.create_journal_entry(
        JournalEntryRequest(
            posting_date=date(2026, 10, 19),
            reference_invoice_id="INV-2026-0013",
            paypal_transaction_id="7HS40927NB358164C",
            description="FX drift variance adjustment for INV-2026-0013",
            currency=CurrencyCode.INR,
            lines=[
                JournalEntryLine(
                    account_code="5900-FX-VARIANCE",
                    account_name="FX Variance Expense",
                    debit=25,
                    credit=0,
                    memo="Settlement short by INR 25.00",
                ),
                JournalEntryLine(
                    account_code="2100-AP-TRADE",
                    account_name="Accounts Payable - Trade",
                    debit=0,
                    credit=25,
                    memo="Clear residual AP balance",
                ),
            ],
        ),
        idempotency_key="recon-INV-2026-0013-20261019",
    )
    # TODO: Handle 'response' of type JournalEntryResponse
except ApiError as e:
    ...  # TODO: Handle 'e.error' of type CreateJournalEntryErrorBody
```

</dd>
</dl>

### Parameters

<dl>
<dd>

| Name | Type | Description |
| --- | --- | --- |
| <code>body</code> | <code>[JournalEntryRequest](ask_your_payments_consolidated_platform_api/models/journal_entry_request.py) \| [JournalEntryRequestDict](ask_your_payments_consolidated_platform_api/models/journal_entry_request.py)</code> | The request body. |
| <code>idempotency_key</code> | <code>str \| None</code> | Unique key to safely retry the request without creating duplicate entries.<br>**Default**: <code>None</code> |
| <code>request_options</code> | <code>[RequestOptionsOrDict](ask_your_payments_consolidated_platform_api/core/request_options.py) \| None</code> | Per-call overrides for this one request, such as a timeout, extra headers, or its retry count and statuses. |

</dd>
</dl>

### Response

<dl>
<dd>

**OnSuccess**: <code>[JournalEntryResponse](ask_your_payments_consolidated_platform_api/models/journal_entry_response.py)</code> -- Journal entry created successfully.

**OnError**: <code>[ApiError](ask_your_payments_consolidated_platform_api/core/exceptions.py)&#91;[CreateJournalEntryErrorBody](ask_your_payments_consolidated_platform_api/errors/create_journal_entry_error.py)&#93;</code>

Mapped in first-match order -- an earlier row wins over a later range that also covers the status:

| Status | `error` is |
| --- | --- |
| 400, 401, 403, 409, 422, 429, 500 | <code>[Error](ask_your_payments_consolidated_platform_api/models/error.py)</code> |
| anything unmapped | <code>[RawError](ask_your_payments_consolidated_platform_api/core/results.py)</code> |

</dd>
</dl>

</dd>
</dl>

</details>

## System

> Source: [System](ask_your_payments_consolidated_platform_api/apis/system.py)

<details>
<summary><code>def health_check_health_get(*, request_options: RequestOptionsOrDict | None = None) -> dict[str, str]</code></summary>

<dl>
<dd>

### Description

<dl>
<dd>

Health check for deployment load balancers and orchestrators.

</dd>
</dl>

### Usage

<dl>
<dd>

**Sync**

```python
try:
    response = client.system.health_check_health_get()
    # TODO: Handle 'response' of type dict[str, str]
except ApiError as e:
    ...  # TODO: Handle 'e.error' of type RawError
```

**Async**

```python
try:
    response = await async_client.system.health_check_health_get()
    # TODO: Handle 'response' of type dict[str, str]
except ApiError as e:
    ...  # TODO: Handle 'e.error' of type RawError
```

</dd>
</dl>

### Parameters

<dl>
<dd>

| Name | Type | Description |
| --- | --- | --- |
| <code>request_options</code> | <code>[RequestOptionsOrDict](ask_your_payments_consolidated_platform_api/core/request_options.py) \| None</code> | Per-call overrides for this one request, such as a timeout, extra headers, or its retry count and statuses. |

</dd>
</dl>

### Response

<dl>
<dd>

**OnSuccess**: <code>dict&#91;str, str&#93;</code> -- Successful Response

**OnError**: <code>[ApiError](ask_your_payments_consolidated_platform_api/core/exceptions.py)&#91;[RawError](ask_your_payments_consolidated_platform_api/core/results.py)&#93;</code>

</dd>
</dl>

</dd>
</dl>

</details>

<details>
<summary><code>def health_check_healthz_get(*, request_options: RequestOptionsOrDict | None = None) -> dict[str, str]</code></summary>

<dl>
<dd>

### Description

<dl>
<dd>

Health check for deployment load balancers and orchestrators.

</dd>
</dl>

### Usage

<dl>
<dd>

**Sync**

```python
try:
    response = client.system.health_check_healthz_get()
    # TODO: Handle 'response' of type dict[str, str]
except ApiError as e:
    ...  # TODO: Handle 'e.error' of type RawError
```

**Async**

```python
try:
    response = await async_client.system.health_check_healthz_get()
    # TODO: Handle 'response' of type dict[str, str]
except ApiError as e:
    ...  # TODO: Handle 'e.error' of type RawError
```

</dd>
</dl>

### Parameters

<dl>
<dd>

| Name | Type | Description |
| --- | --- | --- |
| <code>request_options</code> | <code>[RequestOptionsOrDict](ask_your_payments_consolidated_platform_api/core/request_options.py) \| None</code> | Per-call overrides for this one request, such as a timeout, extra headers, or its retry count and statuses. |

</dd>
</dl>

### Response

<dl>
<dd>

**OnSuccess**: <code>dict&#91;str, str&#93;</code> -- Successful Response

**OnError**: <code>[ApiError](ask_your_payments_consolidated_platform_api/core/exceptions.py)&#91;[RawError](ask_your_payments_consolidated_platform_api/core/results.py)&#93;</code>

</dd>
</dl>

</dd>
</dl>

</details>

## Vendors

> Source: [Vendors](ask_your_payments_consolidated_platform_api/apis/vendors.py)

<details>
<summary><code>def list_vendors(*, active: bool | None = None, search: str | None = None, page: int | None = 1, page_size: int | None = 25, request_options: RequestOptionsOrDict | None = None) -> VendorListResponse</code></summary>

<dl>
<dd>

### Description

<dl>
<dd>

Returns a paginated list of vendors from the ERP vendor master.

</dd>
</dl>

### Usage

<dl>
<dd>

**Sync**

```python
try:
    response = client.vendors.list_vendors(search="Tata")
    # TODO: Handle 'response' of type VendorListResponse
except ApiError as e:
    ...  # TODO: Handle 'e.error' of type ListVendorsErrorBody
```

**Async**

```python
try:
    response = await async_client.vendors.list_vendors(search="Tata")
    # TODO: Handle 'response' of type VendorListResponse
except ApiError as e:
    ...  # TODO: Handle 'e.error' of type ListVendorsErrorBody
```

</dd>
</dl>

### Parameters

<dl>
<dd>

| Name | Type | Description |
| --- | --- | --- |
| <code>active</code> | <code>bool \| None</code> | Filter vendors by active flag.<br>**Default**: <code>None</code> |
| <code>search</code> | <code>str \| None</code> | Case-insensitive partial match on vendor name.<br>**Default**: <code>None</code> |
| <code>page</code> | <code>int \| None</code> | 1-based page number.<br>**Default**: <code>1</code> |
| <code>page_size</code> | <code>int \| None</code> | Number of records per page.<br>**Default**: <code>25</code> |
| <code>request_options</code> | <code>[RequestOptionsOrDict](ask_your_payments_consolidated_platform_api/core/request_options.py) \| None</code> | Per-call overrides for this one request, such as a timeout, extra headers, or its retry count and statuses. |

</dd>
</dl>

### Response

<dl>
<dd>

**OnSuccess**: <code>[VendorListResponse](ask_your_payments_consolidated_platform_api/models/vendor_list_response.py)</code> -- A paginated list of vendors.

**OnError**: <code>[ApiError](ask_your_payments_consolidated_platform_api/core/exceptions.py)&#91;[ListVendorsErrorBody](ask_your_payments_consolidated_platform_api/errors/list_vendors_error.py)&#93;</code>

Mapped in first-match order -- an earlier row wins over a later range that also covers the status:

| Status | `error` is |
| --- | --- |
| 400, 401, 403, 429, 500 | <code>[Error](ask_your_payments_consolidated_platform_api/models/error.py)</code> |
| anything unmapped | <code>[RawError](ask_your_payments_consolidated_platform_api/core/results.py)</code> |

</dd>
</dl>

</dd>
</dl>

</details>

## Webhooks

> Source: [Webhooks](ask_your_payments_consolidated_platform_api/apis/webhooks.py)

<details>
<summary><code>def paypal_webhook_handler_webhook_paypal_post(body: PayPalWebhookPayload | PayPalWebhookPayloadDict, *, request_options: RequestOptionsOrDict | None = None) -> Any</code></summary>

<dl>
<dd>

### Description

<dl>
<dd>

Simulates receiving a PayPal webhook:
  1. Dedupes and records event into BronzeEvent table.
  2. Locates matching Gold reconciliation record by paypal_transaction_id or reference_invoice_id.
  3. Updates match_status to 'matched'.
  4. Broadcasts a 'WEBHOOK_ACK' event to all connected AG Grid WebSockets
     for instant, frame-safe row flashing and status update.

</dd>
</dl>

### Usage

<dl>
<dd>

**Sync**

```python
try:
    response = client.webhooks.paypal_webhook_handler_webhook_paypal_post(
        PayPalWebhookPayload(id="some example string", event_type="some example string", resource={})
    )
    # TODO: Handle 'response' of type Any
except ApiError as e:
    ...  # TODO: Handle 'e.error' of type PaypalWebhookHandlerWebhookPaypalPostErrorBody
```

**Async**

```python
try:
    response = await async_client.webhooks.paypal_webhook_handler_webhook_paypal_post(
        PayPalWebhookPayload(id="some example string", event_type="some example string", resource={})
    )
    # TODO: Handle 'response' of type Any
except ApiError as e:
    ...  # TODO: Handle 'e.error' of type PaypalWebhookHandlerWebhookPaypalPostErrorBody
```

</dd>
</dl>

### Parameters

<dl>
<dd>

| Name | Type | Description |
| --- | --- | --- |
| <code>body</code> | <code>[PayPalWebhookPayload](ask_your_payments_consolidated_platform_api/models/pay_pal_webhook_payload.py) \| [PayPalWebhookPayloadDict](ask_your_payments_consolidated_platform_api/models/pay_pal_webhook_payload.py)</code> | The request body. |
| <code>request_options</code> | <code>[RequestOptionsOrDict](ask_your_payments_consolidated_platform_api/core/request_options.py) \| None</code> | Per-call overrides for this one request, such as a timeout, extra headers, or its retry count and statuses. |

</dd>
</dl>

### Response

<dl>
<dd>

**OnSuccess**: <code>Any</code> -- Successful Response

**OnError**: <code>[ApiError](ask_your_payments_consolidated_platform_api/core/exceptions.py)&#91;[PaypalWebhookHandlerWebhookPaypalPostErrorBody](ask_your_payments_consolidated_platform_api/errors/paypal_webhook_handler_webhook_paypal_post_error.py)&#93;</code>

Mapped in first-match order -- an earlier row wins over a later range that also covers the status:

| Status | `error` is |
| --- | --- |
| 422 | <code>[HttpValidationError](ask_your_payments_consolidated_platform_api/models/http_validation_error.py)</code> |
| anything unmapped | <code>[RawError](ask_your_payments_consolidated_platform_api/core/results.py)</code> |

</dd>
</dl>

</dd>
</dl>

</details>

