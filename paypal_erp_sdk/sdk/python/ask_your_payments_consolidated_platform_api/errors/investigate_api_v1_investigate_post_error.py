from __future__ import annotations

from dataclasses import dataclass
from typing import Final, TypeAlias

from ..core import ErrorMapper, RawError

InvestigateApiV1InvestigatePostErrorBody: TypeAlias = RawError


@dataclass(frozen=True, slots=True)
class _InvestigateApiV1InvestigatePostError:
    def map(self, status_code: int, content: bytes) -> InvestigateApiV1InvestigatePostErrorBody:
        match status_code:
            case 422 | 502:
                return RawError(status_code, content)
            case _:
                return RawError(status_code, content)


investigate_api_v1_investigate_post_error_mapper: Final[
    ErrorMapper[InvestigateApiV1InvestigatePostErrorBody]
] = _InvestigateApiV1InvestigatePostError()
