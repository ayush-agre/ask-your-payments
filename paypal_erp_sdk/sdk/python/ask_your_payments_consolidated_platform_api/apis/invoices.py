from __future__ import annotations

from ..core import (
    ApiResult,
    AsyncRawClient,
    BaseRawResponse,
    Date,
    RawClient,
    RequestOptionsOrDict,
    async_json_decoder,
    json_decoder,
    param,
    unwrap,
)
from ..errors.list_invoices_error import ListInvoicesErrorBody, list_invoices_error_mapper
from ..models.enums.invoice_status import InvoiceStatusOrStr
from ..models.invoice_list_response import InvoiceListResponse
from ..server.server import Server


class Invoices:
    def __init__(self, client: RawClient, server: Server) -> None:
        self._with_raw_response = InvoicesWithRawResponse(client, server)

    def list_invoices(
        self,
        *,
        status: InvoiceStatusOrStr | None = None,
        vendor_id: str | None = None,
        from_date: Date | None = None,
        to_date: Date | None = None,
        page: int | None = 1,
        page_size: int | None = 25,
        request_options: RequestOptionsOrDict | None = None,
    ) -> InvoiceListResponse:
        """Returns a paginated list of AP invoices, optionally filtered by status, vendor, or date range.

        Args:
            status: Filter invoices by status.
            vendor_id: Filter invoices by vendor identifier.
            from_date: Return invoices dated on or after this date (YYYY-MM-DD).
            to_date: Return invoices dated on or before this date (YYYY-MM-DD).
            page: 1-based page number.
            page_size: Number of records per page.
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            A paginated list of invoices.

        Raises:
            ApiError: Bad request. The request is malformed or contains invalid parameters. Unauthorized. Missing or
                invalid bearer token. Forbidden. The caller lacks permission for this operation. Too many requests. Rate
                limit exceeded. Internal server error. ``error`` is ``Error | RawError``."""
        return unwrap(
            self._with_raw_response.list_invoices(
                status=status,
                vendor_id=vendor_id,
                from_date=from_date,
                to_date=to_date,
                page=page,
                page_size=page_size,
                request_options=request_options,
            ),
        )

    @property
    def with_raw_response(self) -> InvoicesWithRawResponse:
        return self._with_raw_response


class AsyncInvoices:
    def __init__(self, client: AsyncRawClient, server: Server) -> None:
        self._with_raw_response = AsyncInvoicesWithRawResponse(client, server)

    async def list_invoices(
        self,
        *,
        status: InvoiceStatusOrStr | None = None,
        vendor_id: str | None = None,
        from_date: Date | None = None,
        to_date: Date | None = None,
        page: int | None = 1,
        page_size: int | None = 25,
        request_options: RequestOptionsOrDict | None = None,
    ) -> InvoiceListResponse:
        """Returns a paginated list of AP invoices, optionally filtered by status, vendor, or date range.

        Args:
            status: Filter invoices by status.
            vendor_id: Filter invoices by vendor identifier.
            from_date: Return invoices dated on or after this date (YYYY-MM-DD).
            to_date: Return invoices dated on or before this date (YYYY-MM-DD).
            page: 1-based page number.
            page_size: Number of records per page.
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            A paginated list of invoices.

        Raises:
            ApiError: Bad request. The request is malformed or contains invalid parameters. Unauthorized. Missing or
                invalid bearer token. Forbidden. The caller lacks permission for this operation. Too many requests. Rate
                limit exceeded. Internal server error. ``error`` is ``Error | RawError``."""
        return unwrap(
            await self._with_raw_response.list_invoices(
                status=status,
                vendor_id=vendor_id,
                from_date=from_date,
                to_date=to_date,
                page=page,
                page_size=page_size,
                request_options=request_options,
            ),
        )

    @property
    def with_raw_response(self) -> AsyncInvoicesWithRawResponse:
        return self._with_raw_response


class InvoicesWithRawResponse(BaseRawResponse[RawClient, Server]):
    def list_invoices(
        self,
        *,
        status: InvoiceStatusOrStr | None = None,
        vendor_id: str | None = None,
        from_date: Date | None = None,
        to_date: Date | None = None,
        page: int | None = 1,
        page_size: int | None = 25,
        request_options: RequestOptionsOrDict | None = None,
    ) -> ApiResult[InvoiceListResponse, ListInvoicesErrorBody]:
        """Returns a paginated list of AP invoices, optionally filtered by status, vendor, or date range.

        Args:
            status: Filter invoices by status.
            vendor_id: Filter invoices by vendor identifier.
            from_date: Return invoices dated on or after this date (YYYY-MM-DD).
            to_date: Return invoices dated on or before this date (YYYY-MM-DD).
            page: 1-based page number.
            page_size: Number of records per page.
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            An ``ApiResult`` holding the deserialized response or the error body."""
        return self._client.execute(
            http_method="GET",
            url_template=self._server.default("/api/invoices"),
            query_params=[
                param[InvoiceStatusOrStr | None]("status", status),
                param[str | None]("vendor_id", vendor_id),
                param[Date | None]("from_date", from_date),
                param[Date | None]("to_date", to_date),
                param[int | None]("page", page),
                param[int | None]("page_size", page_size),
            ],
            decoder=json_decoder[InvoiceListResponse],
            error_mapper=list_invoices_error_mapper,
            request_options=request_options,
        )


class AsyncInvoicesWithRawResponse(BaseRawResponse[AsyncRawClient, Server]):
    async def list_invoices(
        self,
        *,
        status: InvoiceStatusOrStr | None = None,
        vendor_id: str | None = None,
        from_date: Date | None = None,
        to_date: Date | None = None,
        page: int | None = 1,
        page_size: int | None = 25,
        request_options: RequestOptionsOrDict | None = None,
    ) -> ApiResult[InvoiceListResponse, ListInvoicesErrorBody]:
        """Returns a paginated list of AP invoices, optionally filtered by status, vendor, or date range.

        Args:
            status: Filter invoices by status.
            vendor_id: Filter invoices by vendor identifier.
            from_date: Return invoices dated on or after this date (YYYY-MM-DD).
            to_date: Return invoices dated on or before this date (YYYY-MM-DD).
            page: 1-based page number.
            page_size: Number of records per page.
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            An ``ApiResult`` holding the deserialized response or the error body."""
        return await self._client.execute(
            http_method="GET",
            url_template=self._server.default("/api/invoices"),
            query_params=[
                param[InvoiceStatusOrStr | None]("status", status),
                param[str | None]("vendor_id", vendor_id),
                param[Date | None]("from_date", from_date),
                param[Date | None]("to_date", to_date),
                param[int | None]("page", page),
                param[int | None]("page_size", page_size),
            ],
            decoder=async_json_decoder[InvoiceListResponse],
            error_mapper=list_invoices_error_mapper,
            request_options=request_options,
        )
