from __future__ import annotations

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
from ..errors.create_journal_entry_error import CreateJournalEntryErrorBody, create_journal_entry_error_mapper
from ..models.journal_entry_request import JournalEntryRequest, JournalEntryRequestDict
from ..models.journal_entry_response import JournalEntryResponse
from ..server.server import Server


class JournalEntries:
    def __init__(self, client: RawClient, server: Server) -> None:
        self._with_raw_response = JournalEntriesWithRawResponse(client, server)

    def create_journal_entry(
        self,
        body: JournalEntryRequest | JournalEntryRequestDict,
        *,
        idempotency_key: str | None = None,
        request_options: RequestOptionsOrDict | None = None,
    ) -> JournalEntryResponse:
        """Creates a balanced general ledger journal entry, for example to record a reconciled PayPal settlement,
        processing fee, or FX variance adjustment. Total debits must equal total credits.

        Args:
            body: The request body.
            idempotency_key: Unique key to safely retry the request without creating duplicate entries.
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            Journal entry created successfully.

        Raises:
            ApiError: Bad request. The request is malformed or contains invalid parameters. Unauthorized. Missing or
                invalid bearer token. Forbidden. The caller lacks permission for this operation. Conflict. A journal
                entry with the same Idempotency-Key already exists. Unprocessable entity. The entry is syntactically
                valid but violates accounting rules, such as unbalanced debits and credits. Too many requests. Rate
                limit exceeded. Internal server error. ``error`` is ``Error | RawError``."""
        return unwrap(
            self._with_raw_response.create_journal_entry(
                body, idempotency_key=idempotency_key, request_options=request_options
            ),
        )

    @property
    def with_raw_response(self) -> JournalEntriesWithRawResponse:
        return self._with_raw_response


class AsyncJournalEntries:
    def __init__(self, client: AsyncRawClient, server: Server) -> None:
        self._with_raw_response = AsyncJournalEntriesWithRawResponse(client, server)

    async def create_journal_entry(
        self,
        body: JournalEntryRequest | JournalEntryRequestDict,
        *,
        idempotency_key: str | None = None,
        request_options: RequestOptionsOrDict | None = None,
    ) -> JournalEntryResponse:
        """Creates a balanced general ledger journal entry, for example to record a reconciled PayPal settlement,
        processing fee, or FX variance adjustment. Total debits must equal total credits.

        Args:
            body: The request body.
            idempotency_key: Unique key to safely retry the request without creating duplicate entries.
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            Journal entry created successfully.

        Raises:
            ApiError: Bad request. The request is malformed or contains invalid parameters. Unauthorized. Missing or
                invalid bearer token. Forbidden. The caller lacks permission for this operation. Conflict. A journal
                entry with the same Idempotency-Key already exists. Unprocessable entity. The entry is syntactically
                valid but violates accounting rules, such as unbalanced debits and credits. Too many requests. Rate
                limit exceeded. Internal server error. ``error`` is ``Error | RawError``."""
        return unwrap(
            await self._with_raw_response.create_journal_entry(
                body, idempotency_key=idempotency_key, request_options=request_options
            ),
        )

    @property
    def with_raw_response(self) -> AsyncJournalEntriesWithRawResponse:
        return self._with_raw_response


class JournalEntriesWithRawResponse(BaseRawResponse[RawClient, Server]):
    def create_journal_entry(
        self,
        body: JournalEntryRequest | JournalEntryRequestDict,
        *,
        idempotency_key: str | None = None,
        request_options: RequestOptionsOrDict | None = None,
    ) -> ApiResult[JournalEntryResponse, CreateJournalEntryErrorBody]:
        """Creates a balanced general ledger journal entry, for example to record a reconciled PayPal settlement,
        processing fee, or FX variance adjustment. Total debits must equal total credits.

        Args:
            body: The request body.
            idempotency_key: Unique key to safely retry the request without creating duplicate entries.
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            An ``ApiResult`` holding the deserialized response or the error body."""
        return self._client.execute(
            http_method="POST",
            url_template=self._server.default("/api/journal-entries"),
            headers=[param[str | None]("Idempotency-Key", idempotency_key)],
            body=json_body[JournalEntryRequest | JournalEntryRequestDict](body),
            decoder=json_decoder[JournalEntryResponse],
            error_mapper=create_journal_entry_error_mapper,
            request_options=request_options,
        )


class AsyncJournalEntriesWithRawResponse(BaseRawResponse[AsyncRawClient, Server]):
    async def create_journal_entry(
        self,
        body: JournalEntryRequest | JournalEntryRequestDict,
        *,
        idempotency_key: str | None = None,
        request_options: RequestOptionsOrDict | None = None,
    ) -> ApiResult[JournalEntryResponse, CreateJournalEntryErrorBody]:
        """Creates a balanced general ledger journal entry, for example to record a reconciled PayPal settlement,
        processing fee, or FX variance adjustment. Total debits must equal total credits.

        Args:
            body: The request body.
            idempotency_key: Unique key to safely retry the request without creating duplicate entries.
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            An ``ApiResult`` holding the deserialized response or the error body."""
        return await self._client.execute(
            http_method="POST",
            url_template=self._server.default("/api/journal-entries"),
            headers=[param[str | None]("Idempotency-Key", idempotency_key)],
            body=json_body[JournalEntryRequest | JournalEntryRequestDict](body),
            decoder=async_json_decoder[JournalEntryResponse],
            error_mapper=create_journal_entry_error_mapper,
            request_options=request_options,
        )
