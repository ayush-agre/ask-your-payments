"""
ingestion_worker.py – Ask-Your-Payments Data Ingestion & Reconciliation Engine
================================================================================
Team CrackerX · PayPal AI Hackathon 2026

Responsibilities:
  1. CSV Ingestion  – Parse paypal_settlements.csv and erp_export.csv, deduplicate
                      at the Bronze layer, normalise into Silver.
  2. Deterministic Matching – ID-based (reference_invoice_id == internal_invoice_id)
                              and rule-based (amount + currency + date window).
  3. pg_trgm Fuzzy Matching – Trigram similarity on vendor_name / vendor_email for
                              candidates that fail deterministic passes.
  4. Variance Detection     – Compute settled vs ERP amount deltas, classify root cause.
  5. Journal Generation     – Create balanced double-entry journal entries for matched
                              settlements.

Design constraints:
  • NO vector embeddings – all fuzzy matching uses pg_trgm similarity() / % operator.
  • Idempotent – re-running ingestion on the same CSV is safe (Bronze dedup).
  • All monetary arithmetic uses Python Decimal to avoid IEEE-754 drift.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Optional, Sequence

from sqlalchemy import func, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_standalone_session
from models import (
    AnomalySeverity,
    BronzeEvent,
    GoldAnomalyFlag,
    GoldJournalHeader,
    GoldJournalLine,
    GoldReconciliationMatch,
    IngestionSource,
    JournalEntryType,
    JournalStatus,
    MatchMethod,
    MatchStatus,
    RecordType,
    SilverERPInvoice,
    SilverPayPalTransaction,
)

logger = logging.getLogger("ask_your_payments.ingestion_worker")

# ═══════════════════════════════════════════════════════════════════════════
#  CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════

# Trigram similarity threshold – candidates scoring below this are discarded.
TRGM_SIMILARITY_THRESHOLD = Decimal("0.3")

# Variance tolerance for rule-based matching (absolute, in local currency).
VARIANCE_TOLERANCE = Decimal("0.01")

# Date window for rule-based matching (days).
DATE_WINDOW_DAYS = 7

# FX drift threshold: variances ≤ this amount auto-classify as FX_DRIFT.
FX_DRIFT_THRESHOLD = Decimal("25.00")


# ═══════════════════════════════════════════════════════════════════════════
#  UTILITY HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def _sha256(data: str) -> str:
    """Return hex-encoded SHA-256 digest of a string."""
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def _parse_decimal(value: str) -> Decimal:
    """Parse a string into Decimal; raise on garbage."""
    try:
        return Decimal(value.strip())
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"Cannot parse '{value}' as Decimal") from exc


def _parse_timestamp(value: str) -> datetime:
    """Parse ISO-8601 or common timestamp format into UTC timezone-aware datetime."""
    if not value or str(value).strip() in ("—", "-", "N/A", "null", "None"):
        return datetime.now(timezone.utc)
    raw = str(value).strip()
    if raw.endswith("Z") or raw.endswith("z"):
        raw = raw[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(raw)
        return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)
    except Exception:
        pass
    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d",
        "%Y/%m/%d %H:%M:%S",
        "%d-%m-%Y %H:%M:%S",
        "%m/%d/%Y %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
    ):
        try:
            dt = datetime.strptime(raw, fmt)
            return dt.replace(tzinfo=timezone.utc)
        except Exception:
            continue
    return datetime.now(timezone.utc)


def _normalise_erp_status(raw: str) -> str:
    """Canonical uppercased ERP status for reliable filtering."""
    mapping = {
        "paid": "PAID",
        "pending settlement": "PENDING_SETTLEMENT",
        "approved": "APPROVED",
    }
    return mapping.get(raw.strip().lower(), raw.strip().upper())


# ═══════════════════════════════════════════════════════════════════════════
#  1. BRONZE INGESTION (with deduplication)
# ═══════════════════════════════════════════════════════════════════════════

async def ingest_csv_to_bronze(
    session: AsyncSession,
    csv_content: str,
    source: IngestionSource,
    id_column: str,
    ingested_by: str = "system",
    tenant_id: Optional[str] = None,
) -> list[BronzeEvent]:
    """
    Parse a CSV string and insert each row into bronze_events.
    Uses ON CONFLICT DO NOTHING on (source, source_event_id) for deduplication.
    Returns the list of newly created BronzeEvent records.
    """
    reader = csv.DictReader(io.StringIO(csv_content))
    created: list[BronzeEvent] = []

    for row in reader:
        raw_json = json.dumps(row, ensure_ascii=False, sort_keys=True)
        source_event_id = row.get(id_column, "")
        if not source_event_id.strip():
            logger.warning("Skipping row with empty '%s': %s", id_column, row)
            continue

        payload_hash = _sha256(raw_json)

        stmt = pg_insert(BronzeEvent).values(
            source=source.value,
            source_event_id=source_event_id.strip(),
            raw_payload=raw_json,
            payload_hash=payload_hash,
            ingested_by=ingested_by,
            tenant_id=tenant_id,
        ).on_conflict_do_nothing(
            constraint="uq_bronze_source_dedup",
        ).returning(BronzeEvent)

        result = await session.execute(stmt)
        event = result.scalars().first()
        if event:
            created.append(event)
            logger.info(
                "Bronze ingested: source=%s id=%s",
                source.value,
                source_event_id,
            )
        else:
            logger.debug(
                "Bronze dedup skipped: source=%s id=%s",
                source.value,
                source_event_id,
            )

    await session.flush()
    return created


# ═══════════════════════════════════════════════════════════════════════════
#  2. SILVER NORMALISATION
# ═══════════════════════════════════════════════════════════════════════════

async def normalise_paypal_settlements(
    session: AsyncSession,
    bronze_events: list[BronzeEvent],
) -> list[SilverPayPalTransaction]:
    """
    Transform Bronze PayPal settlement events into Silver normalised records.

    CSV columns mapped:
      paypal_transaction_id  →  paypal_transaction_id
      reference_invoice_id   →  reference_invoice_id
      settled_amount         →  settled_amount  (Decimal)
      fee_amount             →  fee_amount      (Decimal)
      currency               →  currency        (ISO 4217)
      timestamp              →  transaction_timestamp
    """
    records: list[SilverPayPalTransaction] = []

    for event in bronze_events:
        row: dict = json.loads(event.raw_payload)

        txn = SilverPayPalTransaction(
            bronze_event_id=event.id,
            paypal_transaction_id=row["paypal_transaction_id"].strip(),
            reference_invoice_id=row.get("reference_invoice_id", "").strip() or None,
            settled_amount=_parse_decimal(row["settled_amount"]),
            fee_amount=_parse_decimal(row["fee_amount"]),
            currency=row["currency"].strip().upper(),
            transaction_timestamp=_parse_timestamp(row["timestamp"]),
            record_type=RecordType.PAYMENT,
        )

        # Upsert: skip if paypal_transaction_id already exists in Silver
        existing = await session.execute(
            select(SilverPayPalTransaction).where(
                SilverPayPalTransaction.paypal_transaction_id == txn.paypal_transaction_id
            )
        )
        if existing.scalars().first() is None:
            session.add(txn)
            records.append(txn)
            logger.info("Silver PayPal: %s", txn.paypal_transaction_id)

    await session.flush()
    return records


async def normalise_erp_invoices(
    session: AsyncSession,
    bronze_events: list[BronzeEvent],
) -> list[SilverERPInvoice]:
    """
    Transform Bronze ERP events into Silver normalised records.

    CSV columns mapped:
      internal_invoice_id  →  internal_invoice_id
      vendor_name          →  vendor_name
      vendor_email         →  vendor_email  (nullable)
      erp_amount           →  erp_amount    (Decimal)
      currency             →  currency      (ISO 4217)
      status               →  erp_status + erp_status_normalised
    """
    records: list[SilverERPInvoice] = []

    for event in bronze_events:
        row: dict = json.loads(event.raw_payload)

        raw_email = row.get("vendor_email", "").strip()
        raw_status = row.get("status", "").strip()

        inv = SilverERPInvoice(
            bronze_event_id=event.id,
            internal_invoice_id=row["internal_invoice_id"].strip(),
            vendor_name=row["vendor_name"].strip(),
            vendor_email=raw_email if raw_email else None,
            erp_amount=_parse_decimal(row["erp_amount"]),
            currency=row["currency"].strip().upper(),
            erp_status=raw_status,
            erp_status_normalised=_normalise_erp_status(raw_status),
        )

        existing = await session.execute(
            select(SilverERPInvoice).where(
                SilverERPInvoice.internal_invoice_id == inv.internal_invoice_id
            )
        )
        if existing.scalars().first() is None:
            session.add(inv)
            records.append(inv)
            logger.info("Silver ERP: %s – %s", inv.internal_invoice_id, inv.vendor_name)

    await session.flush()
    return records


# ═══════════════════════════════════════════════════════════════════════════
#  3. DETERMINISTIC MATCHING (IDs + Rules)
# ═══════════════════════════════════════════════════════════════════════════

async def run_deterministic_matching(
    session: AsyncSession,
) -> list[GoldReconciliationMatch]:
    """
    Pass 1 – ID Match:
      PayPal.reference_invoice_id == ERP.internal_invoice_id

    Pass 2 – Rule Match (for remaining unmatched):
      Same currency + amount within VARIANCE_TOLERANCE + timestamp within DATE_WINDOW_DAYS

    Returns newly created Gold match records.
    """
    matches: list[GoldReconciliationMatch] = []

    # Fetch all Silver records not yet matched
    already_matched_paypal = select(GoldReconciliationMatch.paypal_transaction_id)
    unmatched_paypal = await session.execute(
        select(SilverPayPalTransaction).where(
            SilverPayPalTransaction.id.notin_(already_matched_paypal)
        )
    )
    paypal_txns: Sequence[SilverPayPalTransaction] = unmatched_paypal.scalars().all()

    already_matched_erp = select(GoldReconciliationMatch.erp_invoice_id).where(
        GoldReconciliationMatch.erp_invoice_id.isnot(None)
    )
    unmatched_erp = await session.execute(
        select(SilverERPInvoice).where(
            SilverERPInvoice.id.notin_(already_matched_erp)
        )
    )
    erp_invoices: Sequence[SilverERPInvoice] = unmatched_erp.scalars().all()

    # Build lookup maps
    erp_by_invoice_id: dict[str, SilverERPInvoice] = {
        inv.internal_invoice_id: inv for inv in erp_invoices
    }
    matched_erp_ids: set = set()
    remaining_paypal: list[SilverPayPalTransaction] = []

    # ── Pass 1: Deterministic ID matching ──────────────────────────────
    for txn in paypal_txns:
        if txn.reference_invoice_id and txn.reference_invoice_id in erp_by_invoice_id:
            erp = erp_by_invoice_id[txn.reference_invoice_id]
            variance = txn.settled_amount - erp.erp_amount
            category = _classify_variance(variance, txn.fee_amount)

            match = GoldReconciliationMatch(
                paypal_transaction_id=txn.id,
                erp_invoice_id=erp.id,
                match_method=MatchMethod.DETERMINISTIC_ID,
                match_status=MatchStatus.MATCHED,
                confidence_score=Decimal("1.0000"),
                settled_amount=txn.settled_amount,
                erp_amount=erp.erp_amount,
                variance_amount=variance,
                fee_amount=txn.fee_amount,
                currency=txn.currency,
                variance_category=category,
            )
            session.add(match)
            matches.append(match)
            matched_erp_ids.add(erp.id)
            logger.info(
                "Deterministic ID match: %s ↔ %s (variance=%s %s)",
                txn.paypal_transaction_id,
                erp.internal_invoice_id,
                variance,
                category,
            )
        else:
            remaining_paypal.append(txn)

    # ── Pass 2: Rule-based matching (amount + currency + date window) ──
    available_erp = [inv for inv in erp_invoices if inv.id not in matched_erp_ids]

    for txn in remaining_paypal:
        best_erp: Optional[SilverERPInvoice] = None

        for erp in available_erp:
            if erp.id in matched_erp_ids:
                continue
            if txn.currency != erp.currency:
                continue
            if abs(txn.settled_amount - erp.erp_amount) > VARIANCE_TOLERANCE:
                continue
            # Rule match found
            best_erp = erp
            break

        if best_erp:
            variance = txn.settled_amount - best_erp.erp_amount
            match = GoldReconciliationMatch(
                paypal_transaction_id=txn.id,
                erp_invoice_id=best_erp.id,
                match_method=MatchMethod.DETERMINISTIC_RULE,
                match_status=MatchStatus.MATCHED,
                confidence_score=Decimal("0.9500"),
                settled_amount=txn.settled_amount,
                erp_amount=best_erp.erp_amount,
                variance_amount=variance,
                fee_amount=txn.fee_amount,
                currency=txn.currency,
                variance_category=_classify_variance(variance, txn.fee_amount),
            )
            session.add(match)
            matches.append(match)
            matched_erp_ids.add(best_erp.id)
            logger.info(
                "Deterministic RULE match: %s ↔ %s",
                txn.paypal_transaction_id,
                best_erp.internal_invoice_id,
            )

    await session.flush()
    return matches


# ═══════════════════════════════════════════════════════════════════════════
#  4. PG_TRGM FUZZY CANDIDATE MATCHING
# ═══════════════════════════════════════════════════════════════════════════

async def run_fuzzy_trgm_matching(
    session: AsyncSession,
    similarity_threshold: Decimal = TRGM_SIMILARITY_THRESHOLD,
) -> list[GoldReconciliationMatch]:
    """
    For PayPal transactions still unmatched after deterministic passes,
    use pg_trgm similarity() on vendor_name and vendor_email to find
    candidate ERP invoices.

    SQL generated (conceptually):
      SELECT erp.*, similarity(erp.vendor_name, :search_term) AS sim_score
      FROM silver_erp_invoices erp
      WHERE erp.vendor_name % :search_term        -- GIN trigram index hit
         OR erp.vendor_email % :search_term
      ORDER BY sim_score DESC
      LIMIT 5;

    Matches scoring above the threshold are flagged as REVIEW_REQUIRED
    (not auto-matched) to preserve the human-in-the-loop principle.
    """
    matches: list[GoldReconciliationMatch] = []

    # Find PayPal txns that have no match yet
    already_matched = select(GoldReconciliationMatch.paypal_transaction_id)
    unmatched_result = await session.execute(
        select(SilverPayPalTransaction).where(
            SilverPayPalTransaction.id.notin_(already_matched)
        )
    )
    unmatched_paypal: Sequence[SilverPayPalTransaction] = unmatched_result.scalars().all()

    if not unmatched_paypal:
        logger.info("No unmatched PayPal transactions for fuzzy matching.")
        return matches

    # ERP invoices not yet matched
    already_matched_erp = select(GoldReconciliationMatch.erp_invoice_id).where(
        GoldReconciliationMatch.erp_invoice_id.isnot(None)
    )

    for txn in unmatched_paypal:
        # Build a search term from the reference_invoice_id or transaction_id
        search_term = txn.reference_invoice_id or txn.paypal_transaction_id

        # Use pg_trgm similarity() to find candidates from unmatched ERP invoices
        fuzzy_query = text("""
            SELECT
                id,
                internal_invoice_id,
                vendor_name,
                vendor_email,
                erp_amount,
                currency,
                GREATEST(
                    similarity(vendor_name, :search_term),
                    COALESCE(similarity(vendor_email, :search_term), 0)
                ) AS sim_score
            FROM silver_erp_invoices
            WHERE id NOT IN (
                SELECT erp_invoice_id
                FROM gold_reconciliation_matches
                WHERE erp_invoice_id IS NOT NULL
            )
            AND (
                vendor_name % :search_term
                OR vendor_email % :search_term
                OR similarity(internal_invoice_id, :search_term) > :threshold
            )
            ORDER BY sim_score DESC
            LIMIT 5
        """)

        result = await session.execute(
            fuzzy_query,
            {
                "search_term": search_term,
                "threshold": float(similarity_threshold),
            },
        )
        candidates = result.fetchall()

        if not candidates:
            # Create an unmatched record for visibility
            unmatched = GoldReconciliationMatch(
                paypal_transaction_id=txn.id,
                erp_invoice_id=None,
                match_method=MatchMethod.FUZZY_TRGM,
                match_status=MatchStatus.UNMATCHED,
                confidence_score=Decimal("0.0000"),
                settled_amount=txn.settled_amount,
                erp_amount=None,
                variance_amount=None,
                fee_amount=txn.fee_amount,
                currency=txn.currency,
                variance_category=None,
            )
            session.add(unmatched)
            matches.append(unmatched)
            logger.warning(
                "UNMATCHED: PayPal %s – no fuzzy candidates found.",
                txn.paypal_transaction_id,
            )
            continue

        # Take the top candidate
        best = candidates[0]
        sim_score = Decimal(str(best.sim_score))

        if sim_score >= similarity_threshold:
            # Load the full ERP invoice for the match record
            erp_result = await session.execute(
                select(SilverERPInvoice).where(SilverERPInvoice.id == best.id)
            )
            erp = erp_result.scalars().first()

            if erp:
                variance = txn.settled_amount - erp.erp_amount

                match = GoldReconciliationMatch(
                    paypal_transaction_id=txn.id,
                    erp_invoice_id=erp.id,
                    match_method=MatchMethod.FUZZY_TRGM,
                    match_status=MatchStatus.REVIEW_REQUIRED,
                    confidence_score=sim_score,
                    settled_amount=txn.settled_amount,
                    erp_amount=erp.erp_amount,
                    variance_amount=variance,
                    fee_amount=txn.fee_amount,
                    currency=txn.currency,
                    variance_category=_classify_variance(variance, txn.fee_amount),
                )
                session.add(match)
                matches.append(match)
                logger.info(
                    "Fuzzy TRGM candidate: %s ↔ %s (score=%s, status=REVIEW_REQUIRED)",
                    txn.paypal_transaction_id,
                    erp.internal_invoice_id,
                    sim_score,
                )

    await session.flush()
    return matches


# ═══════════════════════════════════════════════════════════════════════════
#  5. VARIANCE CLASSIFICATION & ANOMALY DETECTION
# ═══════════════════════════════════════════════════════════════════════════

def _classify_variance(
    variance: Decimal,
    fee_amount: Optional[Decimal],
) -> str:
    """
    Classify the root cause of a settlement-vs-invoice variance.

    Categories:
      EXACT        – zero variance
      FEE          – variance equals the processing fee (PayPal took its cut)
      FX_DRIFT     – small residual after fee attribution (≤ FX_DRIFT_THRESHOLD)
      SIGNIFICANT  – requires human investigation
    """
    if variance == Decimal("0"):
        return "EXACT"

    if fee_amount and abs(variance) == abs(fee_amount):
        return "FEE"

    if abs(variance) <= FX_DRIFT_THRESHOLD:
        return "FX_DRIFT"

    return "SIGNIFICANT"


async def detect_anomalies(
    session: AsyncSession,
    new_matches: list[GoldReconciliationMatch],
) -> list[GoldAnomalyFlag]:
    """
    Run rule-based anomaly detection over newly created match records.

    Rules:
      • VARIANCE_SIGNIFICANT: |variance| > 0 and category is SIGNIFICANT
      • MISSING_VENDOR_EMAIL: matched ERP invoice has no vendor_email
      • STATUS_MISMATCH: ERP status is not PAID for a settled PayPal txn
    """
    anomalies: list[GoldAnomalyFlag] = []

    for match in new_matches:
        # Rule: significant variance
        if (
            match.variance_amount is not None
            and match.variance_category == "SIGNIFICANT"
        ):
            flag = GoldAnomalyFlag(
                match_id=match.id,
                paypal_transaction_id=match.paypal_transaction_id,
                erp_invoice_id=match.erp_invoice_id,
                rule_code="VARIANCE_SIGNIFICANT",
                severity=AnomalySeverity.WARNING,
                description=(
                    f"Significant variance of {match.variance_amount} {match.currency} "
                    f"detected between PayPal settlement and ERP invoice."
                ),
                suggested_action="Investigate FX rate, partial refund, or data entry error.",
            )
            session.add(flag)
            anomalies.append(flag)

        # Rule: missing vendor email (blocks payout reissue)
        if match.erp_invoice_id:
            erp_result = await session.execute(
                select(SilverERPInvoice).where(SilverERPInvoice.id == match.erp_invoice_id)
            )
            erp = erp_result.scalars().first()
            if erp and not erp.vendor_email:
                flag = GoldAnomalyFlag(
                    match_id=match.id,
                    erp_invoice_id=match.erp_invoice_id,
                    rule_code="MISSING_VENDOR_EMAIL",
                    severity=AnomalySeverity.CRITICAL,
                    description=(
                        f"Vendor '{erp.vendor_name}' (invoice {erp.internal_invoice_id}) "
                        f"has no email on file. Payout reissue is blocked."
                    ),
                    suggested_action="Update vendor email in ERP before proceeding.",
                )
                session.add(flag)
                anomalies.append(flag)

            # Rule: ERP status not PAID
            if erp and erp.erp_status_normalised != "PAID":
                flag = GoldAnomalyFlag(
                    match_id=match.id,
                    erp_invoice_id=match.erp_invoice_id,
                    rule_code="ERP_STATUS_MISMATCH",
                    severity=AnomalySeverity.WARNING,
                    description=(
                        f"Invoice {erp.internal_invoice_id} has ERP status "
                        f"'{erp.erp_status_normalised}' but PayPal shows settlement."
                    ),
                    suggested_action="Sync ERP status to PAID or investigate hold reason.",
                )
                session.add(flag)
                anomalies.append(flag)

    await session.flush()
    return anomalies


# ═══════════════════════════════════════════════════════════════════════════
#  6. DOUBLE-ENTRY JOURNAL GENERATION
# ═══════════════════════════════════════════════════════════════════════════

async def generate_journals(
    session: AsyncSession,
    matched_records: list[GoldReconciliationMatch],
    created_by: str = "reconciliation_engine",
) -> list[GoldJournalHeader]:
    """
    For each successful match, generate a balanced double-entry journal:

      DEBIT   1100-PAYPAL-CLEARING   (settled_amount)
      CREDIT  2100-ACCOUNTS-PAYABLE  (settled_amount)

    If a fee is present, an additional entry records it:
      DEBIT   6100-PAYMENT-FEES      (fee_amount)
      CREDIT  1100-PAYPAL-CLEARING   (fee_amount)

    All amounts are positive; direction is encoded in entry_type.
    Currency is inherited from the match record.
    """
    journals: list[GoldJournalHeader] = []

    for match in matched_records:
        if match.match_status not in (MatchStatus.MATCHED,):
            continue  # Only journal fully matched records

        # ── Settlement journal ─────────────────────────────────────
        header = GoldJournalHeader(
            match_id=match.id,
            description=(
                f"PayPal settlement reconciliation – "
                f"amount {match.settled_amount} {match.currency}"
            ),
            currency=match.currency,
            status=JournalStatus.DRAFT,
            created_by=created_by,
        )
        session.add(header)
        await session.flush()  # materialise header.id

        # Debit: PayPal Clearing receives the funds
        debit_line = GoldJournalLine(
            journal_header_id=header.id,
            entry_type=JournalEntryType.DEBIT,
            account_code="1100-PAYPAL-CLEARING",
            account_name="PayPal Settlement Clearing Account",
            amount=match.settled_amount,
            currency=match.currency,
            memo=f"Settlement for match {match.id}",
        )
        session.add(debit_line)

        # Credit: Accounts Payable is relieved
        credit_line = GoldJournalLine(
            journal_header_id=header.id,
            entry_type=JournalEntryType.CREDIT,
            account_code="2100-ACCOUNTS-PAYABLE",
            account_name="Accounts Payable",
            amount=match.settled_amount,
            currency=match.currency,
            memo=f"Settlement for match {match.id}",
        )
        session.add(credit_line)

        journals.append(header)

        # ── Fee journal (if applicable) ────────────────────────────
        if match.fee_amount and match.fee_amount > Decimal("0"):
            fee_header = GoldJournalHeader(
                match_id=match.id,
                description=(
                    f"PayPal processing fee – "
                    f"{match.fee_amount} {match.currency}"
                ),
                currency=match.currency,
                status=JournalStatus.DRAFT,
                created_by=created_by,
            )
            session.add(fee_header)
            await session.flush()

            fee_debit = GoldJournalLine(
                journal_header_id=fee_header.id,
                entry_type=JournalEntryType.DEBIT,
                account_code="6100-PAYMENT-FEES",
                account_name="Payment Processing Fees",
                amount=match.fee_amount,
                currency=match.currency,
                memo=f"PayPal fee for match {match.id}",
            )
            session.add(fee_debit)

            fee_credit = GoldJournalLine(
                journal_header_id=fee_header.id,
                entry_type=JournalEntryType.CREDIT,
                account_code="1100-PAYPAL-CLEARING",
                account_name="PayPal Settlement Clearing Account",
                amount=match.fee_amount,
                currency=match.currency,
                memo=f"PayPal fee for match {match.id}",
            )
            session.add(fee_credit)

            journals.append(fee_header)

    await session.flush()
    return journals


# ═══════════════════════════════════════════════════════════════════════════
#  7. FULL PIPELINE ORCHESTRATOR
# ═══════════════════════════════════════════════════════════════════════════

async def run_full_ingestion_pipeline(
    paypal_csv_path: str | Path,
    erp_csv_path: str | Path,
    ingested_by: str = "system",
    tenant_id: Optional[str] = None,
) -> dict:
    """
    End-to-end pipeline:
      1. Ingest PayPal CSV → Bronze (with dedup)
      2. Ingest ERP CSV → Bronze (with dedup)
      3. Normalise Bronze → Silver
      4. Deterministic matching → Gold
      5. Fuzzy pg_trgm matching → Gold (candidates flagged REVIEW_REQUIRED)
      6. Anomaly detection
      7. Journal generation for matched records

    Returns a summary dict with counts at each stage.
    """
    paypal_csv = Path(paypal_csv_path).read_text(encoding="utf-8")
    erp_csv = Path(erp_csv_path).read_text(encoding="utf-8")

    async with get_standalone_session() as session:
        # ── Bronze ingestion ───────────────────────────────────────
        paypal_bronze = await ingest_csv_to_bronze(
            session=session,
            csv_content=paypal_csv,
            source=IngestionSource.PAYPAL_SETTLEMENT_CSV,
            id_column="paypal_transaction_id",
            ingested_by=ingested_by,
            tenant_id=tenant_id,
        )
        erp_bronze = await ingest_csv_to_bronze(
            session=session,
            csv_content=erp_csv,
            source=IngestionSource.ERP_CSV,
            id_column="internal_invoice_id",
            ingested_by=ingested_by,
            tenant_id=tenant_id,
        )

        # ── Silver normalisation ───────────────────────────────────
        silver_paypal = await normalise_paypal_settlements(session, paypal_bronze)
        silver_erp = await normalise_erp_invoices(session, erp_bronze)

        # ── Gold: Deterministic matching ───────────────────────────
        deterministic_matches = await run_deterministic_matching(session)

        # ── Gold: Fuzzy pg_trgm matching ───────────────────────────
        fuzzy_matches = await run_fuzzy_trgm_matching(session)

        all_matches = deterministic_matches + fuzzy_matches

        # ── Gold: Anomaly detection ────────────────────────────────
        anomalies = await detect_anomalies(session, all_matches)

        # ── Gold: Journal generation ───────────────────────────────
        journals = await generate_journals(session, all_matches)

    summary = {
        "bronze_paypal_events": len(paypal_bronze),
        "bronze_erp_events": len(erp_bronze),
        "silver_paypal_records": len(silver_paypal),
        "silver_erp_records": len(silver_erp),
        "deterministic_matches": len(deterministic_matches),
        "fuzzy_trgm_candidates": len(fuzzy_matches),
        "total_matches": len(all_matches),
        "anomalies_detected": len(anomalies),
        "journals_created": len(journals),
    }

    logger.info("Ingestion pipeline complete: %s", json.dumps(summary, indent=2))
    return summary


# ═══════════════════════════════════════════════════════════════════════════
#  CLI ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import asyncio
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    if len(sys.argv) != 3:
        print("Usage: python ingestion_worker.py <paypal_csv> <erp_csv>")
        sys.exit(1)

    result = asyncio.run(run_full_ingestion_pipeline(sys.argv[1], sys.argv[2]))
    print(json.dumps(result, indent=2))
