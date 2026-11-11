from enum import Enum
from typing import Annotated, TypeAlias

from ...core import open_enum_validator


class FilterOperator2(str, Enum):
    """Comparison operator."""

    EQ = "eq"
    NE = "ne"
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    LIKE = "like"
    ILIKE = "ilike"
    IN = "in"
    NOT_IN = "not_in"
    IS_NULL = "is_null"
    IS_NOT_NULL = "is_not_null"
    BETWEEN = "between"

    __str__ = str.__str__


FilterOperator2OrStr: TypeAlias = Annotated[FilterOperator2 | str, open_enum_validator(FilterOperator2)]
