"""
models.py – Ask-Your-Payments Medallion Architecture & Financial Schemas
=========================================================================
Team CrackerX · PayPal AI Hackathon 2026

PostgreSQL Medallion Architecture:
  Bronze  → Raw Event Store       (immutable ingestion log w/ deduplication)
  Silver  → Operational Records   (normalised source of truth)
  Gold    → Accounting Evidence   (double-entry journals, reconciliation results)

Additional schemas:
  • Deterministic & pg_trgm fuzzy matching results
  • Double-Entry Journal Engine (currency-aware debit/credit)
  • Staged Operations with Four-Eyes human approval (Approver ≠ Proposer)
  • Hash-chained Audit Log

Design constraints (from architecture_context.md):
  • NO vector embeddings – fuzzy matching uses pg_trgm trigram similarity only.
  • NO hardcoded secrets or mock keys.
  • All monetary amounts use NUMERIC(19,4) for sub-cent precision.
  • Secrets are never stored in these tables.
"""

from __future__ import annotations

import enum
import uuid as _uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

import sqlalchemy as sa
from sqlalchemy import (
    CheckConstraint,
    Column,
    Index,
    UniqueConstraint,
    text,
)
from sqlmodel import Field, SQLModel


# ═══════════════════════════════════════════════════════════════════════════
#  HELPER TYPES
# ═══════════════════════════════════════════════════════════════════════════

def _uuid_gen() -> _uuid.UUID:
    return _uuid.uuid4()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class IngestionSource(str, enum.Enum):
    """Canonical source discriminator for Bronze events."""
    PAYPAL_TRANSACTION_SEARCH = "paypal_transaction_search"
    PAYPAL_WEBHOOK = "paypal_webhook"
    PAYPAL_SETTLEMENT_CSV = "paypal_settlement_csv"
    ERP_CSV = "erp_csv"
    ERP_API = "erp_api"


class RecordType(str, enum.Enum):
    """Silver-layer record category."""
    PAYMENT = "payment"
    INVOICE = "invoice"
    REFUND = "refund"
    PAYOUT = "payout"
    FEE = "fee"


class MatchMethod(str, enum.Enum):
    """How a reconciliation match was established."""
    DETERMINISTIC_ID = "deterministic_id"
    DETERMINISTIC_RULE = "deterministic_rule"
    FUZZY_TRGM = "fuzzy_trgm"
    MANUAL_REVIEW = "manual_review"


class MatchStatus(str, enum.Enum):
    """Lifecycle state of a match."""
    MATCHED = "matched"
    PARTIAL = "partial"
    UNMATCHED = "unmatched"
    DISPUTED = "disputed"
    REVIEW_REQUIRED = "review_required"


class JournalEntryType(str, enum.Enum):
    """Double-entry leg direction."""
    DEBIT = "debit"
    CREDIT = "credit"


class JournalStatus(str, enum.Enum):
    """Journal lifecycle."""
    DRAFT = "draft"
    POSTED = "posted"
    REVERSED = "reversed"


class OperationStatus(str, enum.Enum):
    """Staged operation state machine."""
    PROPOSED = "proposed"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"
    FAILED = "failed"
    EXPIRED = "expired"


class OperationType(str, enum.Enum):
    """Financial operation categories."""
    REFUND = "refund"
    PAYOUT = "payout"
    CANCEL_AND_REISSUE = "cancel_and_reissue"
    ERP_JOURNAL_ENTRY = "erp_journal_entry"
    FX_ADJUSTMENT = "fx_adjustment"


class AnomalySeverity(str, enum.Enum):
    """Anomaly severity classification."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


# ═══════════════════════════════════════════════════════════════════════════
#  BRONZE LAYER – Raw Event Store
# ═══════════════════════════════════════════════════════════════════════════

class BronzeEvent(SQLModel, table=True):
    """
    Immutable raw event log. Every external payload lands here first.
    Ingestion deduplication is enforced via a UNIQUE constraint on
    (source, source_event_id) so the same webhook / CSV row / API
    response is never double-stored.
    """

    __tablename__ = "bronze_events"
    __table_args__ = (
        UniqueConstraint(
            "source", "source_event_id",
            name="uq_bronze_source_dedup",
        ),
        Index("ix_bronze_source", "source"),
        Index("ix_bronze_ingested_at", "ingested_at"),
        {"schema": None},  # public schema
    )

    id: _uuid.UUID = Field(
        default_factory=_uuid_gen,
        primary_key=True,
        sa_column_kwargs={"server_default": text("gen_random_uuid()")},
    )
    source: IngestionSource = Field(
        ...,
        description="Which adapter produced this event.",
        sa_type=sa.Text,
    )
    source_event_id: str = Field(
        ...,
        max_length=256,
        description="Idempotency key from the source system (txn ID, webhook event_id, CSV row hash).",
    )
    raw_payload: str = Field(
        ...,
        sa_type=sa.Text,
        description="Verbatim JSON or CSV row. Never mutated after write.",
    )
    payload_hash: str = Field(
        ...,
        max_length=128,
        description="SHA-256 digest of raw_payload for integrity verification.",
    )
    ingested_at: datetime = Field(
        default_factory=_utcnow,
        sa_column_kwargs={"server_default": text("now()")},
    )
    ingested_by: Optional[str] = Field(
        default=None,
        max_length=256,
        description="Authenticated user or service principal that performed ingestion.",
    )
    tenant_id: Optional[str] = Field(
        default=None,
        max_length=128,
        description="Tenant discriminator for multi-tenant isolation.",
    )


# ═══════════════════════════════════════════════════════════════════════════
#  SILVER LAYER – Operational Records (Normalised Source of Truth)
# ═══════════════════════════════════════════════════════════════════════════

class SilverPayPalTransaction(SQLModel, table=True):
    """
    Normalised PayPal settlement/transaction record.
    Maps directly to paypal_settlements.csv headers:
      paypal_transaction_id, reference_invoice_id, settled_amount,
      fee_amount, currency, timestamp
    """

    __tablename__ = "silver_paypal_transactions"
    __table_args__ = (
        UniqueConstraint(
            "paypal_transaction_id",
            name="uq_silver_paypal_txn_id",
        ),
        Index("ix_silver_paypal_ref_invoice", "reference_invoice_id"),
        Index("ix_silver_paypal_currency", "currency"),
        # GIN trigram index for fuzzy matching on transaction IDs
        Index(
            "ix_silver_paypal_txn_trgm",
            "paypal_transaction_id",
            postgresql_using="gin",
            postgresql_ops={"paypal_transaction_id": "gin_trgm_ops"},
        ),
        {"schema": None},
    )

    id: _uuid.UUID = Field(
        default_factory=_uuid_gen,
        primary_key=True,
        sa_column_kwargs={"server_default": text("gen_random_uuid()")},
    )
    bronze_event_id: _uuid.UUID = Field(
        ...,
        foreign_key="bronze_events.id",
        description="Lineage pointer back to the raw event.",
    )
    paypal_transaction_id: str = Field(
        ...,
        max_length=64,
        description="PayPal transaction identifier (e.g. 5TY48213HN7261905).",
    )
    reference_invoice_id: Optional[str] = Field(
        default=None,
        max_length=128,
        description="PayPal-side reference to an invoice (e.g. INV-2026-0001).",
    )
    settled_amount: Decimal = Field(
        ...,
        sa_type=sa.Numeric(19, 4),
        description="Net settled amount in minor-unit precision.",
    )
    fee_amount: Decimal = Field(
        ...,
        sa_type=sa.Numeric(19, 4),
        description="PayPal processing fee.",
    )
    currency: str = Field(
        ...,
        max_length=3,
        description="ISO 4217 currency code.",
    )
    transaction_timestamp: datetime = Field(
        ...,
        description="Authoritative timestamp from PayPal.",
    )
    record_type: RecordType = Field(
        default=RecordType.PAYMENT,
        sa_type=sa.Text,
    )
    normalised_at: datetime = Field(
        default_factory=_utcnow,
        sa_column_kwargs={"server_default": text("now()")},
    )


class SilverERPInvoice(SQLModel, table=True):
    """
    Normalised ERP invoice record.
    Maps directly to erp_export.csv headers:
      internal_invoice_id, vendor_name, vendor_email, erp_amount,
      currency, status
    """

    __tablename__ = "silver_erp_invoices"
    __table_args__ = (
        UniqueConstraint(
            "internal_invoice_id",
            name="uq_silver_erp_invoice_id",
        ),
        Index("ix_silver_erp_vendor", "vendor_name"),
        # GIN trigram indexes for fuzzy vendor name and email matching
        Index(
            "ix_silver_erp_vendor_trgm",
            "vendor_name",
            postgresql_using="gin",
            postgresql_ops={"vendor_name": "gin_trgm_ops"},
        ),
        Index(
            "ix_silver_erp_email_trgm",
            "vendor_email",
            postgresql_using="gin",
            postgresql_ops={"vendor_email": "gin_trgm_ops"},
        ),
        {"schema": None},
    )

    id: _uuid.UUID = Field(
        default_factory=_uuid_gen,
        primary_key=True,
        sa_column_kwargs={"server_default": text("gen_random_uuid()")},
    )
    bronze_event_id: _uuid.UUID = Field(
        ...,
        foreign_key="bronze_events.id",
        description="Lineage pointer back to the raw event.",
    )
    internal_invoice_id: str = Field(
        ...,
        max_length=128,
        description="ERP-internal invoice reference (e.g. INV-2026-0001).",
    )
    vendor_name: str = Field(
        ...,
        max_length=512,
        description="Vendor legal / display name from ERP.",
    )
    vendor_email: Optional[str] = Field(
        default=None,
        max_length=512,
        description="Vendor contact email (may be NULL – e.g. HCL, L&T in sample data).",
    )
    erp_amount: Decimal = Field(
        ...,
        sa_type=sa.Numeric(19, 4),
        description="Invoice amount as recorded in the ERP.",
    )
    currency: str = Field(
        ...,
        max_length=3,
        description="ISO 4217 currency code.",
    )
    erp_status: str = Field(
        ...,
        max_length=64,
        description="Raw ERP status string (PAID, paid, Pending Settlement, Approved, etc.).",
    )
    erp_status_normalised: Optional[str] = Field(
        default=None,
        max_length=64,
        description="Uppercased / canonical status for reliable filtering.",
    )
    normalised_at: datetime = Field(
        default_factory=_utcnow,
        sa_column_kwargs={"server_default": text("now()")},
    )


class Transaction(SQLModel, table=True):
    """
    Silver Operational Transaction Record.
    Normalised operational ledger record inserted during CSV ingestion.
    """
    __tablename__ = "silver_transactions"
    __table_args__ = (
        UniqueConstraint("transaction_id", name="uq_silver_transaction_id"),
        Index("ix_silver_txn_status", "erp_status"),
        Index("ix_silver_txn_vendor", "vendor_email"),
        CheckConstraint(
            "approver_email IS NULL OR approver_email != proposer_email",
            name="ck_silver_four_eyes_approver_ne_proposer",
        ),
        {"schema": None},
    )

    id: _uuid.UUID = Field(
        default_factory=_uuid_gen,
        primary_key=True,
        sa_column_kwargs={"server_default": text("gen_random_uuid()")},
    )
    transaction_id: str = Field(..., max_length=128, description="Canonical transaction identifier")
    timestamp: datetime = Field(default_factory=_utcnow, description="Transaction timestamp")
    vendor_email: Optional[str] = Field(default=None, max_length=512)
    amount: Decimal = Field(default=Decimal("0.00"), sa_type=sa.Numeric(19, 4))
    currency: str = Field(default="USD", max_length=3)
    erp_status: str = Field(default="PENDING_APPROVAL", max_length=64)
    notes: Optional[str] = Field(default=None, sa_type=sa.Text)
    failure_reason: Optional[str] = Field(default=None, sa_type=sa.Text, description="Explicit root-cause failure reason")
    proposer_email: str = Field(default="analyst_raghav@finops.corp", max_length=256)
    approver_email: Optional[str] = Field(default=None, max_length=256)
    created_at: datetime = Field(default_factory=_utcnow, sa_column_kwargs={"server_default": text("now()")})


SilverLedger = Transaction


# ═══════════════════════════════════════════════════════════════════════════
#  GOLD LAYER – Reconciliation & Accounting Evidence
# ═══════════════════════════════════════════════════════════════════════════

class GoldReconciliationMatch(SQLModel, table=True):
    """
    Records the result of matching a PayPal settlement to an ERP invoice.

    Matching methods:
      • DETERMINISTIC_ID   – reference_invoice_id == internal_invoice_id
      • DETERMINISTIC_RULE – amount + currency + date-window rules
      • FUZZY_TRGM         – pg_trgm similarity() on vendor_name / email
      • MANUAL_REVIEW      – human override
    """

    __tablename__ = "gold_reconciliation_matches"
    __table_args__ = (
        Index("ix_gold_match_status", "match_status"),
        Index("ix_gold_match_method", "match_method"),
        {"schema": None},
    )

    id: _uuid.UUID = Field(
        default_factory=_uuid_gen,
        primary_key=True,
        sa_column_kwargs={"server_default": text("gen_random_uuid()")},
    )
    paypal_transaction_id: _uuid.UUID = Field(
        ...,
        foreign_key="silver_paypal_transactions.id",
        description="FK → Silver PayPal transaction.",
    )
    erp_invoice_id: Optional[_uuid.UUID] = Field(
        default=None,
        foreign_key="silver_erp_invoices.id",
        description="FK → Silver ERP invoice (NULL if unmatched).",
    )
    match_method: MatchMethod = Field(
        ...,
        sa_type=sa.Text,
        description="Algorithm that produced this match.",
    )
    match_status: MatchStatus = Field(
        ...,
        sa_type=sa.Text,
        description="Current lifecycle state.",
    )
    confidence_score: Optional[Decimal] = Field(
        default=None,
        sa_type=sa.Numeric(5, 4),
        description="Trigram similarity score [0.0000–1.0000] for fuzzy matches.",
    )
    # ----- Variance tracking -----
    settled_amount: Decimal = Field(
        ...,
        sa_type=sa.Numeric(19, 4),
        description="PayPal settled amount snapshot at match time.",
    )
    erp_amount: Optional[Decimal] = Field(
        default=None,
        sa_type=sa.Numeric(19, 4),
        description="ERP invoice amount snapshot at match time.",
    )
    variance_amount: Optional[Decimal] = Field(
        default=None,
        sa_type=sa.Numeric(19, 4),
        description="settled_amount − erp_amount (positive = overpayment).",
    )
    fee_amount: Optional[Decimal] = Field(
        default=None,
        sa_type=sa.Numeric(19, 4),
        description="PayPal fee captured for variance attribution.",
    )
    currency: str = Field(
        ...,
        max_length=3,
    )
    variance_category: Optional[str] = Field(
        default=None,
        max_length=64,
        description="Fee / FX Drift / Timing / Data Entry / Unknown.",
    )
    # ----- Review -----
    reviewed_by: Optional[str] = Field(default=None, max_length=256)
    reviewed_at: Optional[datetime] = Field(default=None)
    review_notes: Optional[str] = Field(default=None, sa_type=sa.Text)
    matched_at: datetime = Field(
        default_factory=_utcnow,
        sa_column_kwargs={"server_default": text("now()")},
    )


class GoldAnomalyFlag(SQLModel, table=True):
    """
    Statistical or rule-based anomaly flags raised during reconciliation.
    Powers the Anomaly Detection → Anomaly-to-Action pipeline.
    """

    __tablename__ = "gold_anomaly_flags"
    __table_args__ = (
        Index("ix_anomaly_severity", "severity"),
        {"schema": None},
    )

    id: _uuid.UUID = Field(
        default_factory=_uuid_gen,
        primary_key=True,
        sa_column_kwargs={"server_default": text("gen_random_uuid()")},
    )
    match_id: Optional[_uuid.UUID] = Field(
        default=None,
        foreign_key="gold_reconciliation_matches.id",
    )
    paypal_transaction_id: Optional[_uuid.UUID] = Field(
        default=None,
        foreign_key="silver_paypal_transactions.id",
    )
    erp_invoice_id: Optional[_uuid.UUID] = Field(
        default=None,
        foreign_key="silver_erp_invoices.id",
    )
    rule_code: str = Field(
        ...,
        max_length=128,
        description="Machine-readable anomaly rule identifier.",
    )
    severity: AnomalySeverity = Field(
        ...,
        sa_type=sa.Text,
    )
    description: str = Field(
        ...,
        sa_type=sa.Text,
    )
    suggested_action: Optional[str] = Field(default=None, sa_type=sa.Text)
    detected_at: datetime = Field(
        default_factory=_utcnow,
        sa_column_kwargs={"server_default": text("now()")},
    )
    resolved_at: Optional[datetime] = Field(default=None)
    resolved_by: Optional[str] = Field(default=None, max_length=256)


# ═══════════════════════════════════════════════════════════════════════════
#  DOUBLE-ENTRY JOURNAL ENGINE (Gold Layer)
# ═══════════════════════════════════════════════════════════════════════════

class GoldJournalHeader(SQLModel, table=True):
    """
    Header for a balanced double-entry journal.
    Each header groups exactly two legs (debit + credit) that must sum to zero.
    Currency-aware: each journal is denominated in a single currency.
    """

    __tablename__ = "gold_journal_headers"
    __table_args__ = (
        Index("ix_journal_status", "status"),
        Index("ix_journal_posted", "posted_at"),
        {"schema": None},
    )

    id: _uuid.UUID = Field(
        default_factory=_uuid_gen,
        primary_key=True,
        sa_column_kwargs={"server_default": text("gen_random_uuid()")},
    )
    match_id: Optional[_uuid.UUID] = Field(
        default=None,
        foreign_key="gold_reconciliation_matches.id",
        description="Links journal to the reconciliation event that triggered it.",
    )
    description: str = Field(
        ...,
        sa_type=sa.Text,
        description="Human-readable narrative (e.g. 'PayPal settlement INV-2026-0001').",
    )
    currency: str = Field(
        ...,
        max_length=3,
        description="ISO 4217 – all legs must share this currency.",
    )
    status: JournalStatus = Field(
        default=JournalStatus.DRAFT,
        sa_type=sa.Text,
    )
    created_by: str = Field(
        ...,
        max_length=256,
        description="User or service that created the journal.",
    )
    created_at: datetime = Field(
        default_factory=_utcnow,
        sa_column_kwargs={"server_default": text("now()")},
    )
    posted_at: Optional[datetime] = Field(default=None)
    reversed_at: Optional[datetime] = Field(default=None)
    reversal_reason: Optional[str] = Field(default=None, sa_type=sa.Text)


class GoldJournalLine(SQLModel, table=True):
    """
    Individual leg of a double-entry journal.
    Constraint: for any journal_header_id, SUM(debit) == SUM(credit).
    This is enforced at the application layer before posting.
    """

    __tablename__ = "gold_journal_lines"
    __table_args__ = (
        Index("ix_jline_header", "journal_header_id"),
        Index("ix_jline_account", "account_code"),
        CheckConstraint(
            "amount > 0",
            name="ck_jline_positive_amount",
        ),
        {"schema": None},
    )

    id: _uuid.UUID = Field(
        default_factory=_uuid_gen,
        primary_key=True,
        sa_column_kwargs={"server_default": text("gen_random_uuid()")},
    )
    journal_header_id: _uuid.UUID = Field(
        ...,
        foreign_key="gold_journal_headers.id",
        description="Parent journal.",
    )
    entry_type: JournalEntryType = Field(
        ...,
        sa_type=sa.Text,
        description="DEBIT or CREDIT.",
    )
    account_code: str = Field(
        ...,
        max_length=64,
        description="Chart-of-accounts code (e.g. '1100-PAYPAL-CLEARING').",
    )
    account_name: str = Field(
        ...,
        max_length=256,
        description="Human-readable account name.",
    )
    amount: Decimal = Field(
        ...,
        sa_type=sa.Numeric(19, 4),
        description="Always positive; direction is determined by entry_type.",
    )
    currency: str = Field(
        ...,
        max_length=3,
    )
    memo: Optional[str] = Field(default=None, sa_type=sa.Text)


# ═══════════════════════════════════════════════════════════════════════════
#  STAGED OPERATIONS & FOUR-EYES HUMAN APPROVAL
# ═══════════════════════════════════════════════════════════════════════════

class StagedOperation(SQLModel, table=True):
    """
    Staged financial command awaiting human approval.

    Security invariants enforced at the DATABASE level:
      1. Approver ≠ Proposer (Four-Eyes principle via CHECK constraint).
      2. Payload hash is captured at proposal time and re-verified at
         execution time to detect tampering.
      3. Status transitions follow a strict state machine.
    """

    __tablename__ = "staged_operations"
    __table_args__ = (
        # ── FOUR-EYES: Approver must differ from Proposer ──────────
        CheckConstraint(
            "approved_by IS NULL OR approved_by != proposed_by",
            name="ck_four_eyes_approver_ne_proposer",
        ),
        # ── Payload hash must be present ───────────────────────────
        CheckConstraint(
            "length(payload_hash) = 64",
            name="ck_payload_hash_sha256",
        ),
        # ── Status guard: cannot approve without approver ──────────
        CheckConstraint(
            "(status != 'approved' AND status != 'executed') OR approved_by IS NOT NULL",
            name="ck_approved_requires_approver",
        ),
        Index("ix_staged_status", "status"),
        Index("ix_staged_proposed_by", "proposed_by"),
        Index("ix_staged_type", "operation_type"),
        {"schema": None},
    )

    id: _uuid.UUID = Field(
        default_factory=_uuid_gen,
        primary_key=True,
        sa_column_kwargs={"server_default": text("gen_random_uuid()")},
        description="Stable Operation ID for idempotency.",
    )
    operation_type: OperationType = Field(
        ...,
        sa_type=sa.Text,
        description="Category of financial command.",
    )
    # ----- Proposal -----
    proposed_by: str = Field(
        ...,
        max_length=256,
        description="Authenticated user who proposed this operation.",
    )
    proposed_at: datetime = Field(
        default_factory=_utcnow,
        sa_column_kwargs={"server_default": text("now()")},
    )
    payload: str = Field(
        ...,
        sa_type=sa.Text,
        description="Serialised JSON command payload.",
    )
    payload_hash: str = Field(
        ...,
        max_length=64,
        description="SHA-256 hex digest of payload. Re-verified before execution.",
    )
    # ----- Approval (Four-Eyes) -----
    status: OperationStatus = Field(
        default=OperationStatus.PROPOSED,
        sa_type=sa.Text,
    )
    approved_by: Optional[str] = Field(
        default=None,
        max_length=256,
        description="Authenticated user who approved. DB constraint: must differ from proposed_by.",
    )
    approved_at: Optional[datetime] = Field(default=None)
    rejection_reason: Optional[str] = Field(default=None, sa_type=sa.Text)
    # ----- Execution -----
    executed_at: Optional[datetime] = Field(default=None)
    execution_result: Optional[str] = Field(default=None, sa_type=sa.Text)
    error_message: Optional[str] = Field(default=None, sa_type=sa.Text)
    retry_count: int = Field(default=0)
    # ----- Lineage -----
    match_id: Optional[_uuid.UUID] = Field(
        default=None,
        foreign_key="gold_reconciliation_matches.id",
        description="Reconciliation match that triggered this operation.",
    )
    anomaly_id: Optional[_uuid.UUID] = Field(
        default=None,
        foreign_key="gold_anomaly_flags.id",
        description="Anomaly flag that triggered this operation.",
    )
    # ----- Policy -----
    amount_limit: Optional[Decimal] = Field(
        default=None,
        sa_type=sa.Numeric(19, 4),
        description="Maximum authorised amount for this operation.",
    )
    currency: Optional[str] = Field(default=None, max_length=3)
    expires_at: Optional[datetime] = Field(
        default=None,
        description="Operation auto-expires if not approved by this time.",
    )


# ═══════════════════════════════════════════════════════════════════════════
#  HASH-CHAINED AUDIT LOG
# ═══════════════════════════════════════════════════════════════════════════

class AuditLog(SQLModel, table=True):
    """
    Append-only, hash-chained audit trail.
    Each entry's `chain_hash` = SHA-256(previous_chain_hash ‖ payload_hash),
    ensuring tamper-evidence across the entire log.
    """

    __tablename__ = "audit_log"
    __table_args__ = (
        Index("ix_audit_entity", "entity_type", "entity_id"),
        Index("ix_audit_actor", "actor"),
        Index("ix_audit_ts", "created_at"),
        {"schema": None},
    )

    id: _uuid.UUID = Field(
        default_factory=_uuid_gen,
        primary_key=True,
        sa_column_kwargs={"server_default": text("gen_random_uuid()")},
    )
    entity_type: str = Field(
        ...,
        max_length=128,
        description="Table or domain object type (e.g. 'staged_operation', 'journal').",
    )
    entity_id: _uuid.UUID = Field(
        ...,
        description="Primary key of the affected entity.",
    )
    action: str = Field(
        ...,
        max_length=64,
        description="CREATE / APPROVE / REJECT / EXECUTE / REVERSE / etc.",
    )
    actor: str = Field(
        ...,
        max_length=256,
        description="Authenticated user or service principal.",
    )
    detail: Optional[str] = Field(
        default=None,
        sa_type=sa.Text,
        description="JSON-serialised diff or contextual detail.",
    )
    payload_hash: str = Field(
        ...,
        max_length=64,
        description="SHA-256 of the detail payload.",
    )
    previous_hash: Optional[str] = Field(
        default=None,
        max_length=64,
        description="chain_hash of the immediately preceding audit entry.",
    )
    chain_hash: str = Field(
        ...,
        max_length=64,
        description="SHA-256(previous_hash ‖ payload_hash). Provides tamper-evidence.",
    )
    created_at: datetime = Field(
        default_factory=_utcnow,
        sa_column_kwargs={"server_default": text("now()")},
    )
    tenant_id: Optional[str] = Field(default=None, max_length=128)


# ═══════════════════════════════════════════════════════════════════════════
#  TRANSACTIONAL OUTBOX (Reliable Async Dispatch)
# ═══════════════════════════════════════════════════════════════════════════

class TransactionalOutbox(SQLModel, table=True):
    """
    Transactional Outbox for reliable, asynchronous dispatch of financial actions
    (e.g., PayPal API settlements) guaranteeing at-least-once delivery with
    PostgreSQL FOR UPDATE SKIP LOCKED workers.
    """
    __tablename__ = "transactional_outbox"
    __table_args__ = (
        Index("ix_outbox_status", "status"),
        Index("ix_outbox_txn_id", "transaction_id"),
        {"schema": None},
    )

    id: _uuid.UUID = Field(
        default_factory=_uuid_gen,
        primary_key=True,
        sa_column_kwargs={"server_default": text("gen_random_uuid()")},
    )
    transaction_id: str = Field(..., max_length=128, description="Target transaction identifier")
    status: str = Field(default="PENDING", max_length=64, description="PENDING, PROCESSING, EXECUTED, FAILED")
    payload: str = Field(..., sa_type=sa.Text, description="Serialized JSON payload for PayPal API dispatch")
    payload_hash: Optional[str] = Field(default=None, max_length=64, description="SHA-256 digest of payload")
    proposer_email: Optional[str] = Field(default=None, max_length=256)
    approver_email: Optional[str] = Field(default=None, max_length=256)
    created_at: datetime = Field(
        default_factory=_utcnow,
        sa_column_kwargs={"server_default": text("now()")},
    )
    processed_at: Optional[datetime] = Field(default=None)
    error_message: Optional[str] = Field(default=None, sa_type=sa.Text)

