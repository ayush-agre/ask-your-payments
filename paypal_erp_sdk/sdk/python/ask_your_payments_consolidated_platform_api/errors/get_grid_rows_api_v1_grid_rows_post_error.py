from __future__ import annotations

from dataclasses import dataclass
from typing import Final, TypeAlias

from ..core import ErrorMapper, RawError, decode_json
from ..models.http_validation_error import HttpValidationError

GetGridRowsApiV1GridRowsPostErrorBody: TypeAlias = HttpValidationError | RawError


@dataclass(frozen=True, slots=True)
class _GetGridRowsApiV1GridRowsPostError:
    def map(self, status_code: int, content: bytes) -> GetGridRowsApiV1GridRowsPostErrorBody:
        match status_code:
            case 422:
                return decode_json[HttpValidationError](content)
            case _:
                return RawError(status_code, content)


get_grid_rows_api_v1_grid_rows_post_error_mapper: Final[
    ErrorMapper[GetGridRowsApiV1GridRowsPostErrorBody]
] = _GetGridRowsApiV1GridRowsPostError()
