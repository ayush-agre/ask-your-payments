from __future__ import annotations

from dataclasses import dataclass
from typing import Final, TypeAlias

from ..core import ErrorMapper, RawError, decode_json
from ..models.http_validation_error import HttpValidationError

OverrideMatchApiV1MatchesMatchIdOverridePatchErrorBody: TypeAlias = HttpValidationError | RawError


@dataclass(frozen=True, slots=True)
class _OverrideMatchApiV1MatchesMatchIdOverridePatchError:
    def map(self, status_code: int, content: bytes) -> OverrideMatchApiV1MatchesMatchIdOverridePatchErrorBody:
        match status_code:
            case 422:
                return decode_json[HttpValidationError](content)
            case _:
                return RawError(status_code, content)


override_match_api_v1_matches_match_id_override_patch_error_mapper: Final[
    ErrorMapper[OverrideMatchApiV1MatchesMatchIdOverridePatchErrorBody]
] = _OverrideMatchApiV1MatchesMatchIdOverridePatchError()
