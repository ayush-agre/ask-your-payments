from enum import Enum
from typing import Annotated, TypeAlias

from ...core import open_enum_validator


class AggregateFunction(str, Enum):
    """Allowlisted aggregate functions."""

    COUNT = "count"
    SUM = "sum"
    AVG = "avg"
    MIN = "min"
    MAX = "max"

    __str__ = str.__str__


AggregateFunctionOrStr: TypeAlias = Annotated[AggregateFunction | str, open_enum_validator(AggregateFunction)]
