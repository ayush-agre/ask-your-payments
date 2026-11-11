from enum import Enum
from typing import Annotated, TypeAlias

from ...core import open_enum_validator


class Status(str, Enum):
    POSTED = "POSTED"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    REVERSED = "REVERSED"

    __str__ = str.__str__


StatusOrStr: TypeAlias = Annotated[Status | str, open_enum_validator(Status)]
