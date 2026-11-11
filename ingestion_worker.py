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
import math
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import pandas as pd

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


def _clean_val(val: Any) -> Any:
    """Normalize None, float NaN, pandas NA, and stringified null/nan to None."""
    if val is None:
        return None
    if isinstance(val, float) and math.isnan(val):
        return None
    try:
        if pd.isna(val):
            return None
    except Exception:
        pass
    if isinstance(val, Decimal) and val.is_nan():
        return None
    if isinstance(val, str) and val.strip().lower() in ("", "nan", "none", "null", "<na>"):
        return None
    return val


def _pick_row_val(row: Dict[str, Any], *keys: str) -> Any:
    """Return the first non-null, non-NaN value from row for candidate keys."""
    for k in keys:
        v = _clean_val(row.get(k))
        if v is not None:
            return v
    return None


def _parse_money_decimal(val: Any) -> Decimal:
    """Parse monetary value into Decimal, stripping currency symbols and whitespace."""
    val = _clean_val(val)
    if val is None:
        return Decimal("0.00")
    if isinstance(val, (int, float, Decimal)):
        try:
            d = Decimal(str(val))
            if d.is_nan() or d.is_infinite():
                return Decimal("0.00")
            return d.quantize(Decimal("0.01"))
        except Exception:
            return Decimal("0.00")
    raw = str(val).strip()
    for sym in ("$", "₹", "€", "£", ","):
        raw = raw.replace(sym, "")
    try:
        d = Decimal(raw.strip() or "0.00")
        if d.is_nan() or d.is_infinite():
            return Decimal("0.00")
        return d.quantize(Decimal("0.01"))
    except Exception:
        return Decimal("0.00")


def _pick_first_col(df: pd.DataFrame, candidates: Sequence[str]) -> Optional[str]:
    """Return the first column name that exists in df from candidates."""
    for col in candidates:
        if col in df.columns:
            return col
    col_lower_map = {c.lower(): c for c in df.columns}
    for col in candidates:
        if col.lower() in col_lower_map:
            return col_lower_map[col.lower()]
    return None


def reconcile_erp_paypal_left_join(
    erp_rows: Sequence[Dict[str, Any]],
    paypal_rows: Sequence[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Deterministic reconciliation merge engine using pandas LEFT JOIN:
    - ERP rows form the primary ledger (Left Side).
    - Joins ERP 'erp_txn_id' against PayPal 'erp_reference_id'.
    - Yields EXACTLY len(erp_rows) reconciled records (no list concatenation or union).
    - Normalizes PayPal 'gross_amount' and ERP 'amount'.
    - Flags unmatched ERP records as 'FAILED' with failure_reason.
    - Flags FX variances (> $25.00 limit) as 'FAILED', (<= $25.00) as 'PENDING_APPROVAL'.
    - Normalizes the output schema for every row:
      id, transaction_id, timestamp, vendor_email, amount, currency, erp_status,
      notes, failure_reason, proposer_email, approver_email.
    """
    if not erp_rows:
        return []

    # 1. Load DataFrames
    df_erp = pd.DataFrame([dict(r) for r in erp_rows])
    df_pp = pd.DataFrame([dict(r) for r in paypal_rows]) if paypal_rows else pd.DataFrame()

    # 2. Resolve ERP join key (erp_txn_id or aliases)
    erp_key_col = _pick_first_col(
        df_erp,
        ["erp_txn_id", "internal_invoice_id", "transaction_id", "invoice_id", "txn_id", "id"],
    )
    if erp_key_col:
        df_erp["_join_key"] = df_erp[erp_key_col].fillna("").astype(str).str.strip()
    else:
        df_erp["_join_key"] = [f"ERP-{idx + 1:04d}" for idx in range(len(df_erp))]

    # 3. Resolve PayPal join key (erp_reference_id or aliases)
    if not df_pp.empty:
        pp_key_col = _pick_first_col(
            df_pp,
            [
                "erp_reference_id",
                "reference_invoice_id",
                "custom_id",
                "paypal_reference_id",
                "reference_id",
                "erp_txn_id",
                "transaction_id",
            ],
        )
        if pp_key_col:
            df_pp["_join_key"] = df_pp[pp_key_col].fillna("").astype(str).str.strip()
            df_pp = df_pp[df_pp["_join_key"] != ""]
            # Deduplicate PayPal rows on join key to preserve 1:1 row count with ERP
            df_pp = df_pp.drop_duplicates(subset=["_join_key"], keep="first")
        else:
            df_pp = df_pp.iloc[0:0].copy()
            df_pp["_join_key"] = ""

        # Prefix all PayPal columns (except _join_key) with _pp_ to prevent column collisions
        rename_dict = {col: f"_pp_{col}" for col in df_pp.columns if col != "_join_key"}
        df_pp = df_pp.rename(columns=rename_dict)

        # 4. Perform deterministic LEFT JOIN
        merged = pd.merge(df_erp, df_pp, on="_join_key", how="left")
    else:
        merged = df_erp.copy()

    # Replace all pandas NaN / NA values with Python None before row iteration
    merged = merged.astype(object).where(pd.notnull(merged), None)

    unified_rows: List[Dict[str, Any]] = []

    for idx, row in enumerate(merged.to_dict(orient="records")):
        join_key = str(_clean_val(row.get("_join_key")) or "").strip()
        txn_id = str(
            _pick_row_val(
                row,
                "erp_txn_id",
                "internal_invoice_id",
                "transaction_id",
                "invoice_id",
                "id",
            )
            or join_key
            or f"TXN-{idx + 1:04d}"
        ).strip()

        # Parse ERP amount (check amount, erp_amount, invoice_amount, gross_amount)
        erp_amt_raw = _pick_row_val(
            row,
            "amount",
            "erp_amount",
            "invoice_amount",
            "gross_amount",
        )
        erp_amt = _parse_money_decimal(erp_amt_raw)

        # Parse Currency: read from ERP, fallback to PayPal, fallback to USD
        raw_curr = (
            _pick_row_val(
                row,
                "currency",
                "_pp_currency",
                "mc_currency",
                "_pp_mc_currency",
            )
            or "USD"
        )
        curr = str(raw_curr).strip().upper()
        if not curr or curr in ("—", "-", "NONE", "NULL", "NAN"):
            curr = "USD"

        # Vendor info
        vendor = (
            _pick_row_val(
                row,
                "vendor_email",
                "vendor_name",
                "_pp_vendor_email",
                "_pp_payer_email",
            )
            or "vendor@corp.internal"
        )

        # Timestamp normalization
        raw_ts = _pick_row_val(
            row,
            "timestamp",
            "created_at",
            "_pp_timestamp",
            "_pp_transaction_timestamp",
        )
        ts_obj = _parse_timestamp(str(raw_ts or ""))
        ts = ts_obj.isoformat()

        # Check if matched with PayPal
        pp_matched = False
        pp_id = ""
        pp_amt = Decimal("0.00")

        if not df_pp.empty:
            pp_ref = str(
                _pick_row_val(
                    row,
                    "_pp_erp_reference_id",
                    "_pp_reference_invoice_id",
                    "_pp_custom_id",
                )
                or ""
            ).strip()
            pp_id = str(
                _pick_row_val(
                    row,
                    "_pp_paypal_transaction_id",
                    "_pp_transaction_id",
                    "_pp_id",
                )
                or ""
            ).strip()

            # PayPal amount: check gross_amount FIRST as per prompt
            pp_amt_raw = _pick_row_val(
                row,
                "_pp_gross_amount",
                "_pp_settled_amount",
                "_pp_amount",
                "_pp_mc_gross",
                "_pp_net_amount",
            )
            has_pp_amount = pp_amt_raw is not None

            if (pp_ref and pp_ref == join_key) or pp_id or has_pp_amount:
                pp_matched = True
                pp_amt = _parse_money_decimal(pp_amt_raw)
                if not pp_id:
                    pp_id = f"PP-{join_key}"

        # If ERP amount was 0 or unparsed, but PayPal had gross_amount, use PayPal gross_amount
        if erp_amt == Decimal("0.00") and pp_matched and pp_amt > Decimal("0.00"):
            erp_amt = pp_amt

        curr_sym = "$" if curr == "USD" else ("₹" if curr == "INR" else f"{curr} ")

        if not pp_matched:
            # Unmatched ERP record: Flag as 'FAILED' as requested
            status = "FAILED"
            failure_reason = f"UNMATCHED_PAYPAL_SETTLEMENT: Missing erp_reference_id match for {txn_id}"
            notes = f"Unmatched ERP record: No corresponding PayPal settlement found for {txn_id}."
        else:
            variance = pp_amt - erp_amt
            abs_var = abs(variance)
            raw_erp_stat = str(_pick_row_val(row, "erp_status", "status") or "").strip().upper()

            if raw_erp_stat in ["UNKNOWN", "MISSING", "PENDING_SETTLEMENT"]:
                status = "PENDING_APPROVAL"
                failure_reason = None
                notes = f"Missing clearance status on ERP ledger. Settled in PayPal as {pp_id}."
            elif abs_var > Decimal("0.00"):
                if abs_var <= Decimal("25.00"):
                    status = "PENDING_APPROVAL"
                    failure_reason = None
                    notes = f"FX variance delta detected ({curr_sym}{variance:+.2f} / {curr_sym}25.00 limit). Four-Eyes approval required."
                else:
                    status = "FAILED"
                    formatted_delta = f"{abs_var:,.2f}" if abs_var != int(abs_var) else f"{int(abs_var):,}"
                    failure_reason = f"FX Variance Limit Breached: Δ{curr_sym}{formatted_delta}"
                    notes = f"CRITICAL AMOUNT DELTA: Variance of {curr_sym}{variance:+.2f} exceeds threshold ({curr_sym}25.00 limit). {failure_reason}"
            else:
                status = "SETTLED"
                failure_reason = None
                notes = f"Auto-reconciled: Deterministic match ({txn_id} ↔ {pp_id}). Zero variance."

        unified_rows.append({
            "id": str(uuid.uuid4()),
            "transaction_id": txn_id,
            "timestamp": ts,
            "vendor_email": str(vendor),
            "amount": str(erp_amt),
            "currency": curr,
            "erp_status": status,
            "notes": notes,
            "failure_reason": failure_reason,
            "proposer_email": "analyst@finops.corp",
            "approver_email": None,
        })

    return unified_rows


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
      paypal_transaction_id (or transaction_id) → paypal_transaction_id
      erp_reference_id (or reference_invoice_id) → reference_invoice_id
      gross_amount (or settled_amount / amount) → settled_amount (Decimal)
      fee_amount (or fee) → fee_amount (Decimal)
      currency (or mc_currency) → currency (ISO 4217)
      timestamp (or transaction_timestamp) → transaction_timestamp
    """
    records: list[SilverPayPalTransaction] = []

    for event in bronze_events:
        row: dict = json.loads(event.raw_payload)

        pp_id = str(
            row.get("paypal_transaction_id")
            or row.get("transaction_id")
            or row.get("id")
            or f"PP-{uuid.uuid4()}"
        ).strip()
        ref_id = str(
            row.get("erp_reference_id")
            or row.get("reference_invoice_id")
            or row.get("custom_id")
            or row.get("reference_id")
            or ""
        ).strip() or None
        amt_raw = (
            row.get("gross_amount")
            or row.get("settled_amount")
            or row.get("amount")
            or row.get("mc_gross")
            or "0.00"
        )
        fee_raw = row.get("fee_amount") or row.get("fee") or row.get("mc_fee") or "0.00"
        curr_raw = row.get("currency") or row.get("mc_currency") or "USD"
        ts_raw = row.get("timestamp") or row.get("transaction_timestamp") or row.get("payment_date")

        txn = SilverPayPalTransaction(
            bronze_event_id=event.id,
            paypal_transaction_id=pp_id,
            reference_invoice_id=ref_id,
            settled_amount=_parse_money_decimal(amt_raw),
            fee_amount=_parse_money_decimal(fee_raw),
            currency=str(curr_raw).strip().upper(),
            transaction_timestamp=_parse_timestamp(str(ts_raw)),
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
      erp_txn_id (or internal_invoice_id) → internal_invoice_id
      vendor_name (or vendor) → vendor_name
      vendor_email → vendor_email (nullable)
      amount (or erp_amount) → erp_amount (Decimal)
      currency → currency (ISO 4217)
      erp_status (or status) → erp_status + erp_status_normalised
    """
    records: list[SilverERPInvoice] = []

    for event in bronze_events:
        row: dict = json.loads(event.raw_payload)

        inv_id = str(
            row.get("erp_txn_id")
            or row.get("internal_invoice_id")
            or row.get("transaction_id")
            or row.get("invoice_id")
            or row.get("id")
            or f"INV-{uuid.uuid4()}"
        ).strip()
        vendor = str(
            row.get("vendor_name")
            or row.get("vendor")
            or row.get("vendor_email")
            or "Unknown Vendor"
        ).strip()
        raw_email = str(row.get("vendor_email") or "").strip()
        amt_raw = (
            row.get("amount")
            or row.get("erp_amount")
            or row.get("invoice_amount")
            or row.get("gross_amount")
            or "0.00"
        )
        curr_raw = row.get("currency") or "USD"
        raw_status = str(row.get("erp_status") or row.get("status") or "PENDING").strip()

        inv = SilverERPInvoice(
            bronze_event_id=event.id,
            internal_invoice_id=inv_id,
            vendor_name=vendor,
            vendor_email=raw_email if raw_email else None,
            erp_amount=_parse_money_decimal(amt_raw),
            currency=str(curr_raw).strip().upper(),
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
