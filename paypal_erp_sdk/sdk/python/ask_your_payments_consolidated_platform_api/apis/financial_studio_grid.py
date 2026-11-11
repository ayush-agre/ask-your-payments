from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

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
from ..errors.get_evidence_detail_api_v1_evidence_match_id_get_error import (
    GetEvidenceDetailApiV1EvidenceMatchIdGetErrorBody,
    get_evidence_detail_api_v1_evidence_match_id_get_error_mapper,
)
from ..errors.get_grid_rows_api_v1_grid_rows_post_error import (
    GetGridRowsApiV1GridRowsPostErrorBody,
    get_grid_rows_api_v1_grid_rows_post_error_mapper,
)
from ..errors.override_match_api_v1_matches_match_id_override_patch_error import (
    OverrideMatchApiV1MatchesMatchIdOverridePatchErrorBody,
    override_match_api_v1_matches_match_id_override_patch_error_mapper,
)
from ..models.override_request_payload import OverrideRequestPayload, OverrideRequestPayloadDict
from ..models.ssrm_request import SsrmRequest, SsrmRequestDict
from ..server.server import Server


class FinancialStudioGrid:
    def __init__(self, client: RawClient, server: Server) -> None:
        self._with_raw_response = FinancialStudioGridWithRawResponse(client, server)

    def get_evidence_detail_api_v1_evidence_match_id_get(
        self, match_id: str, *, request_options: RequestOptionsOrDict | None = None
    ) -> Any:
        """Lazy-loads full audit evidence when a FinOps manager expands a row. Returns ERP Invoice vs. PayPal settlement
        comparison, anomaly flags, and associated double-entry journal lines.

        Args:
            match_id: Value sent with the request.
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            Successful Response

        Raises:
            ApiError: Validation Error ``error`` is ``HttpValidationError | RawError``."""
        return unwrap(
            self._with_raw_response.get_evidence_detail_api_v1_evidence_match_id_get(
                match_id, request_options=request_options
            ),
        )

    def get_grid_rows_api_v1_grid_rows_post(
        self, body: SsrmRequest | SsrmRequestDict, *, request_options: RequestOptionsOrDict | None = None
    ) -> Any:
        """Serves row data directly to AG Grid Server-Side Row Model (SSRM). Supports pagination, multi-column sorting,
        and joins Gold reconciliation matches with Silver PayPal settlements and Silver ERP invoices.

        Args:
            body: The request body.
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            Successful Response

        Raises:
            ApiError: Validation Error ``error`` is ``HttpValidationError | RawError``."""
        return unwrap(
            self._with_raw_response.get_grid_rows_api_v1_grid_rows_post(body, request_options=request_options)
        )

    def override_match_api_v1_matches_match_id_override_patch(
        self,
        match_id: str,
        body: OverrideRequestPayload | OverrideRequestPayloadDict,
        *,
        request_options: RequestOptionsOrDict | None = None,
    ) -> Any:
        """Processes manual FinOps controller overrides inside an AG Grid cell. Stages an operation subject to Four-Eyes
        human verification and broadcasts the updated match status to all connected WebSockets.

        Args:
            match_id: Value sent with the request.
            body: The request body.
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            Successful Response

        Raises:
            ApiError: Validation Error ``error`` is ``HttpValidationError | RawError``."""
        return unwrap(
            self._with_raw_response.override_match_api_v1_matches_match_id_override_patch(
                match_id, body, request_options=request_options
            ),
        )

    @property
    def with_raw_response(self) -> FinancialStudioGridWithRawResponse:
        return self._with_raw_response


class AsyncFinancialStudioGrid:
    def __init__(self, client: AsyncRawClient, server: Server) -> None:
        self._with_raw_response = AsyncFinancialStudioGridWithRawResponse(client, server)

    async def get_evidence_detail_api_v1_evidence_match_id_get(
        self, match_id: str, *, request_options: RequestOptionsOrDict | None = None
    ) -> Any:
        """Lazy-loads full audit evidence when a FinOps manager expands a row. Returns ERP Invoice vs. PayPal settlement
        comparison, anomaly flags, and associated double-entry journal lines.

        Args:
            match_id: Value sent with the request.
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            Successful Response

        Raises:
            ApiError: Validation Error ``error`` is ``HttpValidationError | RawError``."""
        return unwrap(
            await self._with_raw_response.get_evidence_detail_api_v1_evidence_match_id_get(
                match_id, request_options=request_options
            ),
        )

    async def get_grid_rows_api_v1_grid_rows_post(
        self, body: SsrmRequest | SsrmRequestDict, *, request_options: RequestOptionsOrDict | None = None
    ) -> Any:
        """Serves row data directly to AG Grid Server-Side Row Model (SSRM). Supports pagination, multi-column sorting,
        and joins Gold reconciliation matches with Silver PayPal settlements and Silver ERP invoices.

        Args:
            body: The request body.
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            Successful Response

        Raises:
            ApiError: Validation Error ``error`` is ``HttpValidationError | RawError``."""
        return unwrap(
            await self._with_raw_response.get_grid_rows_api_v1_grid_rows_post(body, request_options=request_options)
        )

    async def override_match_api_v1_matches_match_id_override_patch(
        self,
        match_id: str,
        body: OverrideRequestPayload | OverrideRequestPayloadDict,
        *,
        request_options: RequestOptionsOrDict | None = None,
    ) -> Any:
        """Processes manual FinOps controller overrides inside an AG Grid cell. Stages an operation subject to Four-Eyes
        human verification and broadcasts the updated match status to all connected WebSockets.

        Args:
            match_id: Value sent with the request.
            body: The request body.
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            Successful Response

        Raises:
            ApiError: Validation Error ``error`` is ``HttpValidationError | RawError``."""
        return unwrap(
            await self._with_raw_response.override_match_api_v1_matches_match_id_override_patch(
                match_id, body, request_options=request_options
            ),
        )

    @property
    def with_raw_response(self) -> AsyncFinancialStudioGridWithRawResponse:
        return self._with_raw_response


class FinancialStudioGridWithRawResponse(BaseRawResponse[RawClient, Server]):
    def get_evidence_detail_api_v1_evidence_match_id_get(
        self, match_id: str, *, request_options: RequestOptionsOrDict | None = None
    ) -> ApiResult[Any, GetEvidenceDetailApiV1EvidenceMatchIdGetErrorBody]:
        """Lazy-loads full audit evidence when a FinOps manager expands a row. Returns ERP Invoice vs. PayPal settlement
        comparison, anomaly flags, and associated double-entry journal lines.

        Args:
            match_id: Value sent with the request.
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            An ``ApiResult`` holding the deserialized response or the error body."""
        return self._client.execute(
            http_method="GET",
            url_template=self._server.default("/api/v1/evidence/{match_id}"),
            path_params=[param[str]("match_id", match_id)],
            decoder=json_decoder[Any],
            error_mapper=get_evidence_detail_api_v1_evidence_match_id_get_error_mapper,
            request_options=request_options,
        )

    def get_grid_rows_api_v1_grid_rows_post(
        self, body: SsrmRequest | SsrmRequestDict, *, request_options: RequestOptionsOrDict | None = None
    ) -> ApiResult[Any, GetGridRowsApiV1GridRowsPostErrorBody]:
        """Serves row data directly to AG Grid Server-Side Row Model (SSRM). Supports pagination, multi-column sorting,
        and joins Gold reconciliation matches with Silver PayPal settlements and Silver ERP invoices.

        Args:
            body: The request body.
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            An ``ApiResult`` holding the deserialized response or the error body."""
        return self._client.execute(
            http_method="POST",
            url_template=self._server.default("/api/v1/grid/rows"),
            headers=[param[UUID]("Idempotency-Key", uuid4())],
            body=json_body[SsrmRequest | SsrmRequestDict](body),
            decoder=json_decoder[Any],
            error_mapper=get_grid_rows_api_v1_grid_rows_post_error_mapper,
            request_options=request_options,
        )

    def override_match_api_v1_matches_match_id_override_patch(
        self,
        match_id: str,
        body: OverrideRequestPayload | OverrideRequestPayloadDict,
        *,
        request_options: RequestOptionsOrDict | None = None,
    ) -> ApiResult[Any, OverrideMatchApiV1MatchesMatchIdOverridePatchErrorBody]:
        """Processes manual FinOps controller overrides inside an AG Grid cell. Stages an operation subject to Four-Eyes
        human verification and broadcasts the updated match status to all connected WebSockets.

        Args:
            match_id: Value sent with the request.
            body: The request body.
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            An ``ApiResult`` holding the deserialized response or the error body."""
        return self._client.execute(
            http_method="PATCH",
            url_template=self._server.default("/api/v1/matches/{match_id}/override"),
            path_params=[param[str]("match_id", match_id)],
            headers=[param[UUID]("Idempotency-Key", uuid4())],
            body=json_body[OverrideRequestPayload | OverrideRequestPayloadDict](body),
            decoder=json_decoder[Any],
            error_mapper=override_match_api_v1_matches_match_id_override_patch_error_mapper,
            request_options=request_options,
        )


class AsyncFinancialStudioGridWithRawResponse(BaseRawResponse[AsyncRawClient, Server]):
    async def get_evidence_detail_api_v1_evidence_match_id_get(
        self, match_id: str, *, request_options: RequestOptionsOrDict | None = None
    ) -> ApiResult[Any, GetEvidenceDetailApiV1EvidenceMatchIdGetErrorBody]:
        """Lazy-loads full audit evidence when a FinOps manager expands a row. Returns ERP Invoice vs. PayPal settlement
        comparison, anomaly flags, and associated double-entry journal lines.

        Args:
            match_id: Value sent with the request.
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            An ``ApiResult`` holding the deserialized response or the error body."""
        return await self._client.execute(
            http_method="GET",
            url_template=self._server.default("/api/v1/evidence/{match_id}"),
            path_params=[param[str]("match_id", match_id)],
            decoder=async_json_decoder[Any],
            error_mapper=get_evidence_detail_api_v1_evidence_match_id_get_error_mapper,
            request_options=request_options,
        )

    async def get_grid_rows_api_v1_grid_rows_post(
        self, body: SsrmRequest | SsrmRequestDict, *, request_options: RequestOptionsOrDict | None = None
    ) -> ApiResult[Any, GetGridRowsApiV1GridRowsPostErrorBody]:
        """Serves row data directly to AG Grid Server-Side Row Model (SSRM). Supports pagination, multi-column sorting,
        and joins Gold reconciliation matches with Silver PayPal settlements and Silver ERP invoices.

        Args:
            body: The request body.
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            An ``ApiResult`` holding the deserialized response or the error body."""
        return await self._client.execute(
            http_method="POST",
            url_template=self._server.default("/api/v1/grid/rows"),
            headers=[param[UUID]("Idempotency-Key", uuid4())],
            body=json_body[SsrmRequest | SsrmRequestDict](body),
            decoder=async_json_decoder[Any],
            error_mapper=get_grid_rows_api_v1_grid_rows_post_error_mapper,
            request_options=request_options,
        )

    async def override_match_api_v1_matches_match_id_override_patch(
        self,
        match_id: str,
        body: OverrideRequestPayload | OverrideRequestPayloadDict,
        *,
        request_options: RequestOptionsOrDict | None = None,
    ) -> ApiResult[Any, OverrideMatchApiV1MatchesMatchIdOverridePatchErrorBody]:
        """Processes manual FinOps controller overrides inside an AG Grid cell. Stages an operation subject to Four-Eyes
        human verification and broadcasts the updated match status to all connected WebSockets.

        Args:
            match_id: Value sent with the request.
            body: The request body.
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            An ``ApiResult`` holding the deserialized response or the error body."""
        return await self._client.execute(
            http_method="PATCH",
            url_template=self._server.default("/api/v1/matches/{match_id}/override"),
            path_params=[param[str]("match_id", match_id)],
            headers=[param[UUID]("Idempotency-Key", uuid4())],
            body=json_body[OverrideRequestPayload | OverrideRequestPayloadDict](body),
            decoder=async_json_decoder[Any],
            error_mapper=override_match_api_v1_matches_match_id_override_patch_error_mapper,
            request_options=request_options,
        )
