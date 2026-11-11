from enum import Enum
from typing import Annotated, TypeAlias

from ...core import open_enum_validator


class FilterOperator(str, Enum):
    """Allowlisted SQL operators the LLM may use in filter conditions."""

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


FilterOperatorOrStr: TypeAlias = Annotated[FilterOperator | str, open_enum_validator(FilterOperator)]
