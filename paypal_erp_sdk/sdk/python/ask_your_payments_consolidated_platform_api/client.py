from __future__ import annotations

from functools import cached_property
from types import TracebackType

from typing_extensions import Self

from .apis.ai_investigation import AiInvestigation
from .apis.financial_studio_grid import FinancialStudioGrid
from .apis.invoices import Invoices
from .apis.journal_entries import JournalEntries
from .apis.system import System
from .apis.vendors import Vendors
from .apis.webhooks import Webhooks
from .auth import AuthSchemes
from .base_client import DEFAULT_TIMEOUT, BaseAskYourPaymentsConsolidatedPlatformApiClient
from .core import (
    OPERATING_SYSTEM,
    PYTHON_RUNTIME,
    BearerAuthScheme,
    HttpClient,
    Httpx2Client,
    LoggingOptionsOrDict,
    RawClient,
    RetryOptionsOrDict,
    no_auth,
    param,
)
from .server.environment import Environment


class AskYourPaymentsConsolidatedPlatformApiClient(BaseAskYourPaymentsConsolidatedPlatformApiClient[RawClient]):
    def __init__(
        self,
        *,
        environment: Environment = "production",
        base_url: str | None = None,
        timeout: float = DEFAULT_TIMEOUT,
        retry_options: int | RetryOptionsOrDict | None = None,
        logging_options: LoggingOptionsOrDict | None = None,
        custom_http_client: HttpClient | None = None,
        bearer_auth: str | None = None,
    ) -> None:
        super().__init__(
            environment=environment,
            base_url=base_url,
            timeout=timeout,
            retry_options=retry_options,
            logging_options=logging_options,
        )
        self._raw_client = RawClient(
            http_client=custom_http_client if custom_http_client is not None else Httpx2Client(timeout=timeout),
            retry_options=self._retry_options,
            logging_options=self._logging_options,
            global_headers=[
                param[str]("User-Agent", "AskYourPaymentsConsolidatedPlatformApiClient/1.0.0 Python"),
                param[str]("X-APIMatic-Lang", "Python"),
                param[str]("X-APIMatic-Package-Version", "1.0.0"),
                param[str]("X-APIMatic-Gen-Version", "4.0.0"),
                param[str]("X-APIMatic-OS", OPERATING_SYSTEM),
                param[str]("X-APIMatic-Runtime", PYTHON_RUNTIME),
            ],
        )
        self._auth = AuthSchemes(bearer_auth=BearerAuthScheme(bearer_auth) if bearer_auth is not None else no_auth)

    @cached_property
    def ai_investigation(self) -> AiInvestigation:
        return AiInvestigation(self._raw_client, self._server)

    @cached_property
    def financial_studio_grid(self) -> FinancialStudioGrid:
        return FinancialStudioGrid(self._raw_client, self._server)

    @cached_property
    def invoices(self) -> Invoices:
        return Invoices(self._raw_client, self._server)

    @cached_property
    def journal_entries(self) -> JournalEntries:
        return JournalEntries(self._raw_client, self._server)

    @cached_property
    def system(self) -> System:
        return System(self._raw_client, self._server)

    @cached_property
    def vendors(self) -> Vendors:
        return Vendors(self._raw_client, self._server)

    @cached_property
    def webhooks(self) -> Webhooks:
        return Webhooks(self._raw_client, self._server)

    def close(self) -> None:
        self._raw_client.http_client.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self, exc_type: type[BaseException] | None, exc: BaseException | None, exc_tb: TracebackType | None
    ) -> None:
        self.close()


Client = AskYourPaymentsConsolidatedPlatformApiClient
