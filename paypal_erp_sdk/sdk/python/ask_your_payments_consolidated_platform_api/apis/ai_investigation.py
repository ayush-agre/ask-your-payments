from __future__ import annotations

from uuid import UUID, uuid4

from ..core import (
    ApiResult,
    AsyncRawClient,
    BaseRawResponse,
    RawClient,
    RawError,
    RequestOptionsOrDict,
    async_json_decoder,
    json_body,
    json_decoder,
    param,
    raw_error_response,
    unwrap,
)
from ..errors.investigate_api_v1_investigate_post_error import (
    InvestigateApiV1InvestigatePostErrorBody,
    investigate_api_v1_investigate_post_error_mapper,
)
from ..models.investigation_request import InvestigationRequest, InvestigationRequestDict
from ..models.investigation_response import InvestigationResponse
from ..server.server import Server


class AiInvestigation:
    def __init__(self, client: RawClient, server: Server) -> None:
        self._with_raw_response = AiInvestigationWithRawResponse(client, server)

    def ai_health_api_v1_investigate_health_get(
        self, *, request_options: RequestOptionsOrDict | None = None
    ) -> dict[str, str]:
        """Verify the AI investigation router is operational.

        Args:
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            Successful Response

        Raises:
            ApiError: If the API responds with an error status code. ``error`` is ``RawError``."""
        return unwrap(self._with_raw_response.ai_health_api_v1_investigate_health_get(request_options=request_options))

    def investigate_api_v1_investigate_post(
        self,
        body: InvestigationRequest | InvestigationRequestDict,
        *,
        request_options: RequestOptionsOrDict | None = None,
    ) -> InvestigationResponse:
        """Accepts a natural language query from a FinOps manager, applies PII minimisation, sends the sanitised query
        to Gemini 2.5 Flash for intent extraction, and compiles the result into allowlisted parameterised SQL against
        the Silver/Gold operational records.

        Args:
            body: The request body.
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            Successful Response

        Raises:
            ApiError: AI produced invalid schema or query is malformed Gemini API unavailable ``error`` is
                ``RawError``."""
        return unwrap(
            self._with_raw_response.investigate_api_v1_investigate_post(body, request_options=request_options)
        )

    @property
    def with_raw_response(self) -> AiInvestigationWithRawResponse:
        return self._with_raw_response


class AsyncAiInvestigation:
    def __init__(self, client: AsyncRawClient, server: Server) -> None:
        self._with_raw_response = AsyncAiInvestigationWithRawResponse(client, server)

    async def ai_health_api_v1_investigate_health_get(
        self, *, request_options: RequestOptionsOrDict | None = None
    ) -> dict[str, str]:
        """Verify the AI investigation router is operational.

        Args:
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            Successful Response

        Raises:
            ApiError: If the API responds with an error status code. ``error`` is ``RawError``."""
        return unwrap(
            await self._with_raw_response.ai_health_api_v1_investigate_health_get(request_options=request_options)
        )

    async def investigate_api_v1_investigate_post(
        self,
        body: InvestigationRequest | InvestigationRequestDict,
        *,
        request_options: RequestOptionsOrDict | None = None,
    ) -> InvestigationResponse:
        """Accepts a natural language query from a FinOps manager, applies PII minimisation, sends the sanitised query
        to Gemini 2.5 Flash for intent extraction, and compiles the result into allowlisted parameterised SQL against
        the Silver/Gold operational records.

        Args:
            body: The request body.
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            Successful Response

        Raises:
            ApiError: AI produced invalid schema or query is malformed Gemini API unavailable ``error`` is
                ``RawError``."""
        return unwrap(
            await self._with_raw_response.investigate_api_v1_investigate_post(body, request_options=request_options)
        )

    @property
    def with_raw_response(self) -> AsyncAiInvestigationWithRawResponse:
        return self._with_raw_response


class AiInvestigationWithRawResponse(BaseRawResponse[RawClient, Server]):
    def ai_health_api_v1_investigate_health_get(
        self, *, request_options: RequestOptionsOrDict | None = None
    ) -> ApiResult[dict[str, str], RawError]:
        """Verify the AI investigation router is operational.

        Args:
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            An ``ApiResult`` holding the deserialized response or the error body."""
        return self._client.execute(
            http_method="GET",
            url_template=self._server.default("/api/v1/investigate/health"),
            decoder=json_decoder[dict[str, str]],
            error_mapper=raw_error_response,
            request_options=request_options,
        )

    def investigate_api_v1_investigate_post(
        self,
        body: InvestigationRequest | InvestigationRequestDict,
        *,
        request_options: RequestOptionsOrDict | None = None,
    ) -> ApiResult[InvestigationResponse, InvestigateApiV1InvestigatePostErrorBody]:
        """Accepts a natural language query from a FinOps manager, applies PII minimisation, sends the sanitised query
        to Gemini 2.5 Flash for intent extraction, and compiles the result into allowlisted parameterised SQL against
        the Silver/Gold operational records.

        Args:
            body: The request body.
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            An ``ApiResult`` holding the deserialized response or the error body."""
        return self._client.execute(
            http_method="POST",
            url_template=self._server.default("/api/v1/investigate/"),
            headers=[param[UUID]("Idempotency-Key", uuid4())],
            body=json_body[InvestigationRequest | InvestigationRequestDict](body),
            decoder=json_decoder[InvestigationResponse],
            error_mapper=investigate_api_v1_investigate_post_error_mapper,
            request_options=request_options,
        )


class AsyncAiInvestigationWithRawResponse(BaseRawResponse[AsyncRawClient, Server]):
    async def ai_health_api_v1_investigate_health_get(
        self, *, request_options: RequestOptionsOrDict | None = None
    ) -> ApiResult[dict[str, str], RawError]:
        """Verify the AI investigation router is operational.

        Args:
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            An ``ApiResult`` holding the deserialized response or the error body."""
        return await self._client.execute(
            http_method="GET",
            url_template=self._server.default("/api/v1/investigate/health"),
            decoder=async_json_decoder[dict[str, str]],
            error_mapper=raw_error_response,
            request_options=request_options,
        )

    async def investigate_api_v1_investigate_post(
        self,
        body: InvestigationRequest | InvestigationRequestDict,
        *,
        request_options: RequestOptionsOrDict | None = None,
    ) -> ApiResult[InvestigationResponse, InvestigateApiV1InvestigatePostErrorBody]:
        """Accepts a natural language query from a FinOps manager, applies PII minimisation, sends the sanitised query
        to Gemini 2.5 Flash for intent extraction, and compiles the result into allowlisted parameterised SQL against
        the Silver/Gold operational records.

        Args:
            body: The request body.
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            An ``ApiResult`` holding the deserialized response or the error body."""
        return await self._client.execute(
            http_method="POST",
            url_template=self._server.default("/api/v1/investigate/"),
            headers=[param[UUID]("Idempotency-Key", uuid4())],
            body=json_body[InvestigationRequest | InvestigationRequestDict](body),
            decoder=async_json_decoder[InvestigationResponse],
            error_mapper=investigate_api_v1_investigate_post_error_mapper,
            request_options=request_options,
        )
