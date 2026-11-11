from enum import Enum
from typing import Annotated, TypeAlias

from ...core import open_enum_validator


class AllowlistedColumn(str, Enum):
    """Exhaustive whitelist of columns the LLM may reference in filters, sorts, and groupings. Maps to the AG Grid
    Column Whitelist from the architecture.

    Organised by source table for clarity."""

    PAYPAL_TRANSACTION_ID = "paypal_transaction_id"
    REFERENCE_INVOICE_ID = "reference_invoice_id"
    SETTLED_AMOUNT = "settled_amount"
    FEE_AMOUNT = "fee_amount"
    CURRENCY = "currency"
    TRANSACTION_TIMESTAMP = "transaction_timestamp"
    RECORD_TYPE = "record_type"
    INTERNAL_INVOICE_ID = "internal_invoice_id"
    VENDOR_NAME = "vendor_name"
    VENDOR_EMAIL = "vendor_email"
    ERP_AMOUNT = "erp_amount"
    ERP_STATUS = "erp_status"
    ERP_STATUS_NORMALISED = "erp_status_normalised"
    MATCH_METHOD = "match_method"
    MATCH_STATUS = "match_status"
    CONFIDENCE_SCORE = "confidence_score"
    VARIANCE_AMOUNT = "variance_amount"
    VARIANCE_CATEGORY = "variance_category"
    MATCHED_AT = "matched_at"
    RULE_CODE = "rule_code"
    SEVERITY = "severity"
    SUGGESTED_ACTION = "suggested_action"
    DETECTED_AT = "detected_at"
    STATUS = "status"
    ACCOUNT_CODE = "account_code"
    ENTRY_TYPE = "entry_type"
    AMOUNT = "amount"

    __str__ = str.__str__


AllowlistedColumnOrStr: TypeAlias = Annotated[AllowlistedColumn | str, open_enum_validator(AllowlistedColumn)]
