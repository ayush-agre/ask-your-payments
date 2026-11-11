from __future__ import annotations

from ..core import (
    ApiResult,
    AsyncRawClient,
    BaseRawResponse,
    RawClient,
    RequestOptionsOrDict,
    async_json_decoder,
    json_decoder,
    param,
    unwrap,
)
from ..errors.list_vendors_error import ListVendorsErrorBody, list_vendors_error_mapper
from ..models.vendor_list_response import VendorListResponse
from ..server.server import Server


class Vendors:
    def __init__(self, client: RawClient, server: Server) -> None:
        self._with_raw_response = VendorsWithRawResponse(client, server)

    def list_vendors(
        self,
        *,
        active: bool | None = None,
        search: str | None = None,
        page: int | None = 1,
        page_size: int | None = 25,
        request_options: RequestOptionsOrDict | None = None,
    ) -> VendorListResponse:
        """Returns a paginated list of vendors from the ERP vendor master.

        Args:
            active: Filter vendors by active flag.
            search: Case-insensitive partial match on vendor name.
            page: 1-based page number.
            page_size: Number of records per page.
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            A paginated list of vendors.

        Raises:
            ApiError: Bad request. The request is malformed or contains invalid parameters. Unauthorized. Missing or
                invalid bearer token. Forbidden. The caller lacks permission for this operation. Too many requests. Rate
                limit exceeded. Internal server error. ``error`` is ``Error | RawError``."""
        return unwrap(
            self._with_raw_response.list_vendors(
                active=active, search=search, page=page, page_size=page_size, request_options=request_options
            ),
        )

    @property
    def with_raw_response(self) -> VendorsWithRawResponse:
        return self._with_raw_response


class AsyncVendors:
    def __init__(self, client: AsyncRawClient, server: Server) -> None:
        self._with_raw_response = AsyncVendorsWithRawResponse(client, server)

    async def list_vendors(
        self,
        *,
        active: bool | None = None,
        search: str | None = None,
        page: int | None = 1,
        page_size: int | None = 25,
        request_options: RequestOptionsOrDict | None = None,
    ) -> VendorListResponse:
        """Returns a paginated list of vendors from the ERP vendor master.

        Args:
            active: Filter vendors by active flag.
            search: Case-insensitive partial match on vendor name.
            page: 1-based page number.
            page_size: Number of records per page.
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            A paginated list of vendors.

        Raises:
            ApiError: Bad request. The request is malformed or contains invalid parameters. Unauthorized. Missing or
                invalid bearer token. Forbidden. The caller lacks permission for this operation. Too many requests. Rate
                limit exceeded. Internal server error. ``error`` is ``Error | RawError``."""
        return unwrap(
            await self._with_raw_response.list_vendors(
                active=active, search=search, page=page, page_size=page_size, request_options=request_options
            ),
        )

    @property
    def with_raw_response(self) -> AsyncVendorsWithRawResponse:
        return self._with_raw_response


class VendorsWithRawResponse(BaseRawResponse[RawClient, Server]):
    def list_vendors(
        self,
        *,
        active: bool | None = None,
        search: str | None = None,
        page: int | None = 1,
        page_size: int | None = 25,
        request_options: RequestOptionsOrDict | None = None,
    ) -> ApiResult[VendorListResponse, ListVendorsErrorBody]:
        """Returns a paginated list of vendors from the ERP vendor master.

        Args:
            active: Filter vendors by active flag.
            search: Case-insensitive partial match on vendor name.
            page: 1-based page number.
            page_size: Number of records per page.
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            An ``ApiResult`` holding the deserialized response or the error body."""
        return self._client.execute(
            http_method="GET",
            url_template=self._server.default("/api/vendors"),
            query_params=[
                param[bool | None]("active", active),
                param[str | None]("search", search),
                param[int | None]("page", page),
                param[int | None]("page_size", page_size),
            ],
            decoder=json_decoder[VendorListResponse],
            error_mapper=list_vendors_error_mapper,
            request_options=request_options,
        )


class AsyncVendorsWithRawResponse(BaseRawResponse[AsyncRawClient, Server]):
    async def list_vendors(
        self,
        *,
        active: bool | None = None,
        search: str | None = None,
        page: int | None = 1,
        page_size: int | None = 25,
        request_options: RequestOptionsOrDict | None = None,
    ) -> ApiResult[VendorListResponse, ListVendorsErrorBody]:
        """Returns a paginated list of vendors from the ERP vendor master.

        Args:
            active: Filter vendors by active flag.
            search: Case-insensitive partial match on vendor name.
            page: 1-based page number.
            page_size: Number of records per page.
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            An ``ApiResult`` holding the deserialized response or the error body."""
        return await self._client.execute(
            http_method="GET",
            url_template=self._server.default("/api/vendors"),
            query_params=[
                param[bool | None]("active", active),
                param[str | None]("search", search),
                param[int | None]("page", page),
                param[int | None]("page_size", page_size),
            ],
            decoder=async_json_decoder[VendorListResponse],
            error_mapper=list_vendors_error_mapper,
            request_options=request_options,
        )
