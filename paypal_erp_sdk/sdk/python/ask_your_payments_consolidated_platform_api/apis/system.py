from __future__ import annotations

from ..core import (
    ApiResult,
    AsyncRawClient,
    BaseRawResponse,
    RawClient,
    RawError,
    RequestOptionsOrDict,
    async_json_decoder,
    json_decoder,
    raw_error_response,
    unwrap,
)
from ..server.server import Server


class System:
    def __init__(self, client: RawClient, server: Server) -> None:
        self._with_raw_response = SystemWithRawResponse(client, server)

    def health_check_health_get(self, *, request_options: RequestOptionsOrDict | None = None) -> dict[str, str]:
        """Health check for deployment load balancers and orchestrators.

        Args:
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            Successful Response

        Raises:
            ApiError: If the API responds with an error status code. ``error`` is ``RawError``."""
        return unwrap(self._with_raw_response.health_check_health_get(request_options=request_options))

    def health_check_healthz_get(self, *, request_options: RequestOptionsOrDict | None = None) -> dict[str, str]:
        """Health check for deployment load balancers and orchestrators.

        Args:
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            Successful Response

        Raises:
            ApiError: If the API responds with an error status code. ``error`` is ``RawError``."""
        return unwrap(self._with_raw_response.health_check_healthz_get(request_options=request_options))

    @property
    def with_raw_response(self) -> SystemWithRawResponse:
        return self._with_raw_response


class AsyncSystem:
    def __init__(self, client: AsyncRawClient, server: Server) -> None:
        self._with_raw_response = AsyncSystemWithRawResponse(client, server)

    async def health_check_health_get(self, *, request_options: RequestOptionsOrDict | None = None) -> dict[str, str]:
        """Health check for deployment load balancers and orchestrators.

        Args:
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            Successful Response

        Raises:
            ApiError: If the API responds with an error status code. ``error`` is ``RawError``."""
        return unwrap(await self._with_raw_response.health_check_health_get(request_options=request_options))

    async def health_check_healthz_get(self, *, request_options: RequestOptionsOrDict | None = None) -> dict[str, str]:
        """Health check for deployment load balancers and orchestrators.

        Args:
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            Successful Response

        Raises:
            ApiError: If the API responds with an error status code. ``error`` is ``RawError``."""
        return unwrap(await self._with_raw_response.health_check_healthz_get(request_options=request_options))

    @property
    def with_raw_response(self) -> AsyncSystemWithRawResponse:
        return self._with_raw_response


class SystemWithRawResponse(BaseRawResponse[RawClient, Server]):
    def health_check_health_get(
        self, *, request_options: RequestOptionsOrDict | None = None
    ) -> ApiResult[dict[str, str], RawError]:
        """Health check for deployment load balancers and orchestrators.

        Args:
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            An ``ApiResult`` holding the deserialized response or the error body."""
        return self._client.execute(
            http_method="GET",
            url_template=self._server.default("/health"),
            decoder=json_decoder[dict[str, str]],
            error_mapper=raw_error_response,
            request_options=request_options,
        )

    def health_check_healthz_get(
        self, *, request_options: RequestOptionsOrDict | None = None
    ) -> ApiResult[dict[str, str], RawError]:
        """Health check for deployment load balancers and orchestrators.

        Args:
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            An ``ApiResult`` holding the deserialized response or the error body."""
        return self._client.execute(
            http_method="GET",
            url_template=self._server.default("/healthz"),
            decoder=json_decoder[dict[str, str]],
            error_mapper=raw_error_response,
            request_options=request_options,
        )


class AsyncSystemWithRawResponse(BaseRawResponse[AsyncRawClient, Server]):
    async def health_check_health_get(
        self, *, request_options: RequestOptionsOrDict | None = None
    ) -> ApiResult[dict[str, str], RawError]:
        """Health check for deployment load balancers and orchestrators.

        Args:
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            An ``ApiResult`` holding the deserialized response or the error body."""
        return await self._client.execute(
            http_method="GET",
            url_template=self._server.default("/health"),
            decoder=async_json_decoder[dict[str, str]],
            error_mapper=raw_error_response,
            request_options=request_options,
        )

    async def health_check_healthz_get(
        self, *, request_options: RequestOptionsOrDict | None = None
    ) -> ApiResult[dict[str, str], RawError]:
        """Health check for deployment load balancers and orchestrators.

        Args:
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            An ``ApiResult`` holding the deserialized response or the error body."""
        return await self._client.execute(
            http_method="GET",
            url_template=self._server.default("/healthz"),
            decoder=async_json_decoder[dict[str, str]],
            error_mapper=raw_error_response,
            request_options=request_options,
        )
