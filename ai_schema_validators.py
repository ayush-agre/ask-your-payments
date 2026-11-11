"""
ai_schema_validators.py – AI-to-Grid Contract & PII Minimisation Schemas
==========================================================================
Team CrackerX · PayPal AI Hackathon 2026

This module defines:
  1. PII Minimisation & Untrusted Text Isolation types
  2. The AI-to-Grid Contract – Pydantic schemas that strictly confine Gemini's output
  3. Allowlisted column/table/operator enumerations for the Read-Only Query Compiler
  4. Investigation response schemas for the AG Grid Financial Investigation Studio

Architecture reference (§3 AI Investigation):
  • The LLM's output is strictly confined by Pydantic Schema Validation.
  • Read-Only Query Compiler generates allowlisted SQL.
  • Directly powers the AG Grid Financial Investigation Studio.
"""

from __future__ import annotations

import enum
import re
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# ═══════════════════════════════════════════════════════════════════════════
#  1. PII MINIMISATION & UNTRUSTED TEXT ISOLATION
# ═══════════════════════════════════════════════════════════════════════════

# Regex patterns for PII detection in user queries
_EMAIL_PATTERN: re.Pattern[str] = re.compile(
    r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+",
)
_PHONE_PATTERN: re.Pattern[str] = re.compile(
    r"\b(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}\b",
)
_CREDIT_CARD_PATTERN: re.Pattern[str] = re.compile(
    r"\b(?:\d{4}[-\s]?){3}\d{4}\b",
)
_SSN_PATTERN: re.Pattern[str] = re.compile(
    r"\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b",
)
_AADHAAR_PATTERN: re.Pattern[str] = re.compile(
    r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}\b",
)
_PAN_PATTERN: re.Pattern[str] = re.compile(
    r"\b[A-Z]{5}\d{4}[A-Z]\b",
)
# Bank account / IBAN patterns
_IBAN_PATTERN: re.Pattern[str] = re.compile(
    r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b",
)
_BANK_ACCOUNT_PATTERN: re.Pattern[str] = re.compile(
    r"\b\d{9,18}\b",
)

# Replacement tokens for scrubbed PII
_PII_REPLACEMENTS: dict[str, re.Pattern[str]] = {
    "[EMAIL_REDACTED]": _EMAIL_PATTERN,
    "[PHONE_REDACTED]": _PHONE_PATTERN,
    "[CARD_REDACTED]": _CREDIT_CARD_PATTERN,
    "[SSN_REDACTED]": _SSN_PATTERN,
    "[AADHAAR_REDACTED]": _AADHAAR_PATTERN,
    "[PAN_REDACTED]": _PAN_PATTERN,
    "[IBAN_REDACTED]": _IBAN_PATTERN,
}


class PIIMinimisationResult(BaseModel):
    """Result of PII scrubbing applied to untrusted user input."""

    original_length: int = Field(
        ..., description="Character count of the original query."
    )
    sanitised_query: str = Field(
        ..., description="Query with PII tokens replaced."
    )
    pii_detected: list[str] = Field(
        default_factory=list,
        description="List of PII categories detected and redacted.",
    )
    was_modified: bool = Field(
        ..., description="True if any PII was detected and scrubbed."
    )


def minimise_pii(raw_query: str) -> PIIMinimisationResult:
    """
    Scrub PII from untrusted user input BEFORE it reaches the LLM.

    This function implements the PII Minimisation layer from the architecture:
      - Emails, phone numbers, credit cards, SSN, Aadhaar, PAN, IBAN
      - Each detected category is replaced with a bracketed token
      - The LLM never sees raw PII values

    Returns a PIIMinimisationResult with the sanitised query and audit metadata.
    """
    sanitised: str = raw_query
    categories_detected: list[str] = []

    for replacement_token, pattern in _PII_REPLACEMENTS.items():
        if pattern.search(sanitised):
            category: str = replacement_token.strip("[]").replace("_", " ").title()
            categories_detected.append(category)
            sanitised = pattern.sub(replacement_token, sanitised)

    return PIIMinimisationResult(
        original_length=len(raw_query),
        sanitised_query=sanitised,
        pii_detected=categories_detected,
        was_modified=len(categories_detected) > 0,
    )


class UntrustedTextEnvelope(BaseModel):
    """
    Wraps any untrusted text (user query, LLM output) in an isolation envelope.
    Prevents prompt injection by treating the content as opaque data, not instructions.
    """

    content: str = Field(
        ..., description="The untrusted text content."
    )
    source: Literal["user_query", "llm_output", "external_api"] = Field(
        ..., description="Origin of the untrusted text."
    )
    sanitised: bool = Field(
        default=False, description="Whether PII minimisation has been applied."
    )
    isolation_boundary: str = Field(
        default="<<<UNTRUSTED_INPUT_START>>>",
        description="Delimiter marking the boundary of untrusted content.",
    )

    def render_isolated(self) -> str:
        """Render the content wrapped in isolation delimiters for the LLM prompt."""
        return (
            f"<<<UNTRUSTED_INPUT_START>>>\n"
            f"{self.content}\n"
            f"<<<UNTRUSTED_INPUT_END>>>"
        )


# ═══════════════════════════════════════════════════════════════════════════
#  2. ALLOWLISTED ENUMERATIONS (Read-Only Query Compiler)
# ═══════════════════════════════════════════════════════════════════════════

class AllowlistedTable(str, enum.Enum):
    """
    Tables the LLM is allowed to query. Restricted to Silver (operational
    source of truth) and Gold (accounting evidence) layers.
    Bronze is excluded – raw payloads must never be exposed to the AI.
    """
    SILVER_PAYPAL_TRANSACTIONS = "silver_paypal_transactions"
    SILVER_ERP_INVOICES = "silver_erp_invoices"
    SILVER_TRANSACTIONS = "silver_transactions"
    GOLD_RECONCILIATION_MATCHES = "gold_reconciliation_matches"
    GOLD_ANOMALY_FLAGS = "gold_anomaly_flags"
    GOLD_JOURNAL_HEADERS = "gold_journal_headers"
    GOLD_JOURNAL_LINES = "gold_journal_lines"


class AllowlistedColumn(str, enum.Enum):
    """
    Exhaustive whitelist of columns the LLM may reference in filters, sorts,
    and groupings. Maps to the AG Grid Column Whitelist from the architecture.

    Organised by source table for clarity.
    """
    # -- silver_paypal_transactions --
    PAYPAL_TRANSACTION_ID = "paypal_transaction_id"
    REFERENCE_INVOICE_ID = "reference_invoice_id"
    SETTLED_AMOUNT = "settled_amount"
    FEE_AMOUNT = "fee_amount"
    CURRENCY = "currency"
    TRANSACTION_TIMESTAMP = "transaction_timestamp"
    RECORD_TYPE = "record_type"

    # -- silver_erp_invoices --
    INTERNAL_INVOICE_ID = "internal_invoice_id"
    VENDOR_NAME = "vendor_name"
    VENDOR_EMAIL = "vendor_email"
    ERP_AMOUNT = "erp_amount"
    ERP_STATUS = "erp_status"
    ERP_STATUS_NORMALISED = "erp_status_normalised"

    # -- silver_transactions (unified ledger) --
    TRANSACTION_ID = "transaction_id"
    FAILURE_REASON = "failure_reason"
    NOTES = "notes"
    PROPOSER_EMAIL = "proposer_email"
    APPROVER_EMAIL = "approver_email"
    TIMESTAMP = "timestamp"

    # -- gold_reconciliation_matches --
    MATCH_METHOD = "match_method"
    MATCH_STATUS = "match_status"
    CONFIDENCE_SCORE = "confidence_score"
    VARIANCE_AMOUNT = "variance_amount"
    VARIANCE_CATEGORY = "variance_category"
    MATCHED_AT = "matched_at"

    # -- gold_anomaly_flags --
    RULE_CODE = "rule_code"
    SEVERITY = "severity"
    SUGGESTED_ACTION = "suggested_action"
    DETECTED_AT = "detected_at"

    # -- gold_journal_headers / lines --
    JOURNAL_STATUS = "status"
    ACCOUNT_CODE = "account_code"
    ENTRY_TYPE = "entry_type"
    AMOUNT = "amount"


class FilterOperator(str, enum.Enum):
    """Allowlisted SQL operators the LLM may use in filter conditions."""
    EQUALS = "eq"
    NOT_EQUALS = "ne"
    GREATER_THAN = "gt"
    GREATER_THAN_OR_EQUAL = "gte"
    LESS_THAN = "lt"
    LESS_THAN_OR_EQUAL = "lte"
    LIKE = "like"
    ILIKE = "ilike"
    IN = "in"
    NOT_IN = "not_in"
    IS_NULL = "is_null"
    IS_NOT_NULL = "is_not_null"
    BETWEEN = "between"


class SortDirection(str, enum.Enum):
    """Sort direction."""
    ASC = "asc"
    DESC = "desc"


class AggregateFunction(str, enum.Enum):
    """Allowlisted aggregate functions."""
    COUNT = "count"
    SUM = "sum"
    AVG = "avg"
    MIN = "min"
    MAX = "max"


# ═══════════════════════════════════════════════════════════════════════════
#  3. AI-TO-GRID CONTRACT – LLM Output Schema
# ═══════════════════════════════════════════════════════════════════════════

class FilterCondition(BaseModel):
    """A single filter condition the LLM wants applied to the query."""

    column: AllowlistedColumn = Field(
        ..., description="Column to filter on (must be from the whitelist)."
    )
    operator: FilterOperator = Field(
        ..., description="Comparison operator."
    )
    value: Optional[Any] = Field(
        default=None,
        description=(
            "Filter value. Required for all operators except is_null/is_not_null. "
            "For 'in'/'not_in', provide a list. For 'between', provide [low, high]."
        ),
    )

    @field_validator("value", mode="before")
    @classmethod
    def validate_value_for_operator(cls, v: Any, info: Any) -> Any:
        """Ensure value is present when required by the operator."""
        # We cannot access other fields in a field_validator in Pydantic v2
        # before mode, so we validate in the model_validator below.
        return v

    @model_validator(mode="after")
    def check_value_presence(self) -> "FilterCondition":
        """Ensure value is semantically valid for the chosen operator."""
        nullary_ops = {FilterOperator.IS_NULL, FilterOperator.IS_NOT_NULL}
        if self.operator not in nullary_ops and self.value is None:
            raise ValueError(
                f"Operator '{self.operator.value}' requires a non-null value."
            )
        if self.operator == FilterOperator.BETWEEN:
            if not isinstance(self.value, list) or len(self.value) != 2:
                raise ValueError(
                    "Operator 'between' requires a list of exactly 2 values [low, high]."
                )
        if self.operator in {FilterOperator.IN, FilterOperator.NOT_IN}:
            if not isinstance(self.value, list):
                raise ValueError(
                    f"Operator '{self.operator.value}' requires a list of values."
                )
        return self


class SortSpec(BaseModel):
    """A single sort specification."""

    column: AllowlistedColumn = Field(
        ..., description="Column to sort by."
    )
    direction: SortDirection = Field(
        default=SortDirection.ASC, description="Sort direction."
    )


class GroupSpec(BaseModel):
    """A grouping specification for server-side grouping in AG Grid."""

    column: AllowlistedColumn = Field(
        ..., description="Column to group by."
    )
    aggregate: Optional[AggregateFunction] = Field(
        default=None, description="Aggregate function to apply to grouped rows."
    )
    aggregate_column: Optional[AllowlistedColumn] = Field(
        default=None, description="Column to aggregate (required if aggregate is set)."
    )

    @model_validator(mode="after")
    def check_aggregate_column(self) -> "GroupSpec":
        """Ensure aggregate_column is present when aggregate is specified."""
        if self.aggregate is not None and self.aggregate_column is None:
            raise ValueError(
                "aggregate_column is required when aggregate function is specified."
            )
        return self


class InvestigationIntent(BaseModel):
    """
    The AI-to-Grid Contract – the ONLY schema Gemini is allowed to produce.

    This Pydantic model is the physical decoupling boundary between
    probabilistic AI reasoning and deterministic financial execution.
    The LLM produces structured intent; the Read-Only Query Compiler
    translates it into allowlisted, parameterised SQLAlchemy queries.

    The LLM NEVER sees or produces SQL.
    """

    # ── Query targeting ────────────────────────────────────────────
    target_table: AllowlistedTable = Field(
        ...,
        description=(
            "Primary table to query. The LLM selects from the allowlisted "
            "Silver/Gold tables only."
        ),
    )
    join_tables: list[AllowlistedTable] = Field(
        default_factory=list,
        description="Additional tables to JOIN (the compiler resolves FK relationships).",
    )

    # ── Filter Model (maps to AG Grid filterModel) ─────────────────
    filters: list[FilterCondition] = Field(
        default_factory=list,
        description="WHERE clause conditions. All are ANDed together.",
    )

    # ── Sort Model ─────────────────────────────────────────────────
    sorts: list[SortSpec] = Field(
        default_factory=list,
        description="ORDER BY specifications.",
    )

    # ── Grouping (Server-Side Grouping for AG Grid SSRM) ──────────
    groups: list[GroupSpec] = Field(
        default_factory=list,
        description="GROUP BY with optional aggregates for the SSRM datasource.",
    )

    # ── Pagination ─────────────────────────────────────────────────
    limit: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Maximum rows to return (maps to AG Grid block size).",
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="Pagination offset.",
    )

    # ── AI explanation (human-readable) ────────────────────────────
    explanation: str = Field(
        ...,
        min_length=10,
        description=(
            "Human-readable explanation of what this investigation does, "
            "suitable for display in the AG Grid Investigation Studio."
        ),
    )

    # ── Suggested actions (Anomaly-to-Action Mapping) ─────────────
    suggested_actions: list[str] = Field(
        default_factory=list,
        description="Recommended follow-up actions for the FinOps manager.",
    )

    @field_validator("filters")
    @classmethod
    def limit_filter_count(cls, v: list[FilterCondition]) -> list[FilterCondition]:
        """Prevent excessively complex queries from the LLM."""
        if len(v) > 20:
            raise ValueError("Maximum 20 filter conditions allowed per investigation.")
        return v

    @field_validator("sorts")
    @classmethod
    def limit_sort_count(cls, v: list[SortSpec]) -> list[SortSpec]:
        """Prevent excessive sort columns."""
        if len(v) > 5:
            raise ValueError("Maximum 5 sort specifications allowed.")
        return v


class ProposeOverridePayload(BaseModel):
    """Structured parameters extracted for ACTION_PROPOSE_OVERRIDE intent."""

    transaction_id: str = Field(
        ...,
        description="Target transaction or invoice ID (e.g. TXN-010, INV-004).",
    )
    override_status: str = Field(
        default="SETTLED",
        description="Target override status (e.g. SETTLED, EXECUTED, FAILED).",
    )
    reason: str = Field(
        ...,
        description="Maker's notes and justification explaining why the override is proposed.",
    )
    staged_operation_id: Optional[str] = Field(
        default=None,
        description="UUID of the StagedOperation record created in the transactional outbox.",
    )
    proposer: Optional[str] = Field(
        default=None,
        description="Email or identifier of the user who proposed the override.",
    )


class CopilotInvestigationOutput(BaseModel):
    """
    Structured Copilot output returned by Gemini.
    Separates the technical compiled database intent from the human-facing conversational response.
    """
    intent_type: Literal["DATA_QUERY", "FINANCIAL_QA", "OFF_TOPIC", "ACTION_PROPOSE_OVERRIDE"] = Field(
        default="DATA_QUERY",
        description=(
            "Classifier intent type: 'DATA_QUERY' for grid filter/discrepancy queries, "
            "'FINANCIAL_QA' for project architecture/reconciliation questions, "
            "'OFF_TOPIC' for queries unrelated to finance, reconciliation, coding, or this project, "
            "'ACTION_PROPOSE_OVERRIDE' when the user proposes a Four-Eyes override."
        ),
    )
    compiled_intent: Optional[InvestigationIntent] = Field(
        default=None,
        description=(
            "The structured technical query and filter specification for the database compiler. "
            "Populated ONLY for DATA_QUERY. Must be empty/null for FINANCIAL_QA, OFF_TOPIC, and ACTION_PROPOSE_OVERRIDE."
        ),
    )
    propose_override: Optional[ProposeOverridePayload] = Field(
        default=None,
        description=(
            "Structured parameters extracted for ACTION_PROPOSE_OVERRIDE intent. "
            "Contains transaction_id, override_status, and reason."
        ),
    )
    ui_payload: Optional[dict[str, Any]] = Field(
        default=None,
        description="Optional structured UI payload for Generative UI (e.g. data_table).",
    )
    human_response: str = Field(
        ...,
        description=(
            "Professional conversational text response. "
            "For DATA_QUERY: concise explanation of what is filtered. "
            "For FINANCIAL_QA: thorough, professional answer. "
            "For OFF_TOPIC: must be exactly 'I am a strict B2B FinOps Copilot. I can only assist with ledger reconciliation and financial architecture queries.' "
            "For ACTION_PROPOSE_OVERRIDE: clear explanation that the Four-Eyes override proposal has been staged."
        ),
    )


# ═══════════════════════════════════════════════════════════════════════════
#  4. INVESTIGATION REQUEST & RESPONSE SCHEMAS
# ═══════════════════════════════════════════════════════════════════════════

class InvestigationRequest(BaseModel):
    """Inbound request from the FinOps manager."""

    query: str = Field(
        ...,
        min_length=3,
        max_length=2000,
        description="Natural language investigation query.",
    )
    tenant_id: Optional[str] = Field(
        default=None,
        max_length=128,
        description="Tenant context for multi-tenant isolation.",
    )
    requested_by: str = Field(
        default="anonymous",
        max_length=256,
        description="Authenticated user initiating the investigation.",
    )
    user_email: Optional[str] = Field(
        default=None,
        max_length=256,
        description="Optional email of user initiating the investigation.",
    )
    user_role: Optional[str] = Field(
        default=None,
        max_length=64,
        description="Role of the user (e.g. Maker, Checker).",
    )
    max_results: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Maximum rows the user wants returned.",
    )

    @field_validator("query")
    @classmethod
    def reject_sql_injection_keywords(cls, v: str) -> str:
        """
        Defence-in-depth: reject queries containing raw SQL keywords.
        This is NOT a substitute for parameterised queries – it's an
        additional signal that untrusted input may be adversarial.
        """
        dangerous_patterns: list[str] = [
            "DROP TABLE", "DELETE FROM", "INSERT INTO", "UPDATE SET",
            "ALTER TABLE", "TRUNCATE", "EXEC ", "EXECUTE ",
            "--", ";--", "/*", "*/", "xp_", "sp_",
        ]
        upper_query: str = v.upper()
        for pattern in dangerous_patterns:
            if pattern.upper() in upper_query:
                raise ValueError(
                    f"Query contains potentially dangerous pattern: '{pattern}'. "
                    f"Please rephrase your investigation in natural language."
                )
        return v


class InvestigationResultRow(BaseModel):
    """A single row in the investigation result set."""

    data: dict[str, Any] = Field(
        ..., description="Column name → value mapping for this row."
    )


class InvestigationResponse(BaseModel):
    """Complete response from the AI Investigation pipeline."""

    investigation_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for this investigation.",
    )
    original_query: str = Field(
        ..., description="The user's original query (PII-scrubbed)."
    )
    intent_type: Literal["DATA_QUERY", "FINANCIAL_QA", "OFF_TOPIC", "ACTION_PROPOSE_OVERRIDE"] = Field(
        default="DATA_QUERY",
        description="Classifier intent type: DATA_QUERY, FINANCIAL_QA, OFF_TOPIC, or ACTION_PROPOSE_OVERRIDE.",
    )
    human_response: str = Field(
        ...,
        description="A short, professional natural language string explaining what the copilot is doing.",
    )
    propose_override: Optional[ProposeOverridePayload] = Field(
        default=None,
        description="Structured override action block when intent_type is ACTION_PROPOSE_OVERRIDE.",
    )
    action_payload: Optional[dict[str, Any]] = Field(
        default=None,
        description="Generic action metadata dictionary for generative UI blocks.",
    )
    ui_payload: Optional[dict[str, Any]] = Field(
        default=None,
        description="Structured Generative UI payload (e.g. ui_type: 'data_table' with interactive dataset rows).",
    )
    compiled_intent: Optional[InvestigationIntent] = Field(
        default=None,
        description="The structured technical query and filter specification for the database compiler.",
    )
    ai_explanation: Optional[str] = Field(
        default=None, description="Gemini's human-readable explanation of the investigation (legacy alias)."
    )
    intent: Optional[InvestigationIntent] = Field(
        default=None, description="The structured AI-to-Grid Contract that was compiled (legacy alias)."
    )
    suggested_actions: list[str] = Field(
        default_factory=list,
        description="AI-suggested follow-up actions.",
    )

    # ── Result data ────────────────────────────────────────────────
    columns: list[str] = Field(
        default_factory=list, description="Ordered list of column names in the result set."
    )
    rows: list[InvestigationResultRow] = Field(
        default_factory=list, description="Result rows."
    )
    total_count: int = Field(
        default=0, description="Total rows matching (before pagination)."
    )

    # ── KPI aggregates for AG Grid widgets ─────────────────────────
    kpi: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Pre-computed KPI aggregates: total_trapped_working_capital, "
            "dollars_reconciled, dollars_requiring_review."
        ),
    )

    # ── Audit metadata ─────────────────────────────────────────────
    pii_scrubbed: bool = Field(
        default=False, description="Whether PII minimisation was applied."
    )
    pii_categories: list[str] = Field(
        default_factory=list, description="PII categories that were detected and scrubbed."
    )
    executed_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp of query execution.",
    )
    query_duration_ms: Optional[float] = Field(
        default=None, description="Database query execution time in milliseconds."
    )
