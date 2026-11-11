from __future__ import annotations

from dataclasses import dataclass
from typing import Final, TypeAlias

from ..core import ErrorMapper, RawError, decode_json
from ..models.http_validation_error import HttpValidationError

GetEvidenceDetailApiV1EvidenceMatchIdGetErrorBody: TypeAlias = HttpValidationError | RawError


@dataclass(frozen=True, slots=True)
class _GetEvidenceDetailApiV1EvidenceMatchIdGetError:
    def map(self, status_code: int, content: bytes) -> GetEvidenceDetailApiV1EvidenceMatchIdGetErrorBody:
        match status_code:
            case 422:
                return decode_json[HttpValidationError](content)
            case _:
                return RawError(status_code, content)


get_evidence_detail_api_v1_evidence_match_id_get_error_mapper: Final[
    ErrorMapper[GetEvidenceDetailApiV1EvidenceMatchIdGetErrorBody]
] = _GetEvidenceDetailApiV1EvidenceMatchIdGetError()
