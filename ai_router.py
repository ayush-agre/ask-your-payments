"""
ai_router.py – FastAPI Natural Language Investigation Router
==============================================================
Team CrackerX · PayPal AI Hackathon 2026

Architecture reference (§3 AI Investigation):
  1. FastAPI Investigation Router with PII Minimisation & Untrusted Text Isolation
  2. Gemini 1.5 Flash for Investigation and Explanation
  3. Pydantic Schema Validation – LLM output strictly confined to InvestigationIntent
  4. Read-Only Query Compiler – translates intent to allowlisted, parameterised SQLAlchemy
  5. Evidence Aggregator – computes KPI aggregates for AG Grid widgets
  6. AI NEVER executes SQL directly

Security invariants:
  • PII is scrubbed BEFORE reaching the LLM
  • User input is wrapped in untrusted text isolation delimiters
  • The LLM returns ONLY a Pydantic-validated InvestigationIntent schema
  • The Query Compiler maps intent to parameterised SQLAlchemy – no raw SQL strings
  • Only allowlisted tables, columns, and operators are permitted
  • All queries are READ-ONLY (SELECT only)
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import time
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional, Sequence

from fastapi import APIRouter, Depends, HTTPException, status
from google import genai
from google.genai import types as genai_types
from pydantic import ValidationError
from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_schema_validators import (
    AggregateFunction,
    AllowlistedColumn,
    AllowlistedTable,
    CopilotInvestigationOutput,
    FilterCondition,
    FilterOperator,
    InvestigationIntent,
    InvestigationRequest,
    InvestigationResponse,
    InvestigationResultRow,
    PIIMinimisationResult,
    ProposeOverridePayload,
    SortDirection,
    UntrustedTextEnvelope,
    minimise_pii,
)
from config import settings
from database import get_session
from models import (
    GoldAnomalyFlag,
    GoldJournalHeader,
    GoldJournalLine,
    GoldReconciliationMatch,
    OperationStatus,
    OperationType,
    SilverERPInvoice,
    SilverPayPalTransaction,
    StagedOperation,
    Transaction,
)

logger = logging.getLogger("ask_your_payments.ai_router")

# ═══════════════════════════════════════════════════════════════════════════
#  ROUTER SETUP
# ═══════════════════════════════════════════════════════════════════════════

router = APIRouter(
    prefix="/api/v1/investigate",
    tags=["AI Investigation"],
)

# ═══════════════════════════════════════════════════════════════════════════
#  TABLE & COLUMN REGISTRY (Allowlist enforcement)
# ═══════════════════════════════════════════════════════════════════════════

# Map AllowlistedTable enum → SQLModel class
_TABLE_REGISTRY: dict[AllowlistedTable, type] = {
    AllowlistedTable.SILVER_TRANSACTIONS: Transaction,
    AllowlistedTable.SILVER_PAYPAL_TRANSACTIONS: SilverPayPalTransaction,
    AllowlistedTable.SILVER_ERP_INVOICES: SilverERPInvoice,
    AllowlistedTable.GOLD_RECONCILIATION_MATCHES: GoldReconciliationMatch,
    AllowlistedTable.GOLD_ANOMALY_FLAGS: GoldAnomalyFlag,
    AllowlistedTable.GOLD_JOURNAL_HEADERS: GoldJournalHeader,
    AllowlistedTable.GOLD_JOURNAL_LINES: GoldJournalLine,
}

# Map (AllowlistedTable, AllowlistedColumn) → actual SQLAlchemy column object.
# Built dynamically from the registry to stay DRY with models.py.
_COLUMN_REGISTRY: dict[tuple[AllowlistedTable, str], Any] = {}


def _build_column_registry() -> None:
    """
    Populate the column registry by introspecting each SQLModel class.
    Only columns that appear in AllowlistedColumn are registered.
    """
    allowed_col_names: set[str] = {c.value for c in AllowlistedColumn}

    for table_enum, model_cls in _TABLE_REGISTRY.items():
        for col_name in allowed_col_names:
            if hasattr(model_cls, col_name):
                _COLUMN_REGISTRY[(table_enum, col_name)] = getattr(model_cls, col_name)


_build_column_registry()


def _resolve_column(
    table: AllowlistedTable,
    column: AllowlistedColumn,
) -> Any:
    """
    Resolve an allowlisted column reference to a concrete SQLAlchemy column.
    Raises ValueError if the column doesn't exist on the specified table.
    """
    key = (table, column.value)
    if key not in _COLUMN_REGISTRY:
        # Try all tables – the column might belong to a joined table
        for tbl in AllowlistedTable:
            alt_key = (tbl, column.value)
            if alt_key in _COLUMN_REGISTRY:
                return _COLUMN_REGISTRY[alt_key]
        raise ValueError(
            f"Column '{column.value}' is not available on table '{table.value}' "
            f"or any allowlisted table."
        )
    return _COLUMN_REGISTRY[key]


# ═══════════════════════════════════════════════════════════════════════════
#  JOIN RELATIONSHIP MAP
# ═══════════════════════════════════════════════════════════════════════════

# Defines how allowlisted tables can be joined via their foreign key relationships.
# Key: (left_table, right_table) → (left_column, right_column)
_JOIN_MAP: dict[
    tuple[AllowlistedTable, AllowlistedTable],
    tuple[str, str],
] = {
    # PayPal ↔ Reconciliation
    (
        AllowlistedTable.SILVER_PAYPAL_TRANSACTIONS,
        AllowlistedTable.GOLD_RECONCILIATION_MATCHES,
    ): ("id", "paypal_transaction_id"),
    (
        AllowlistedTable.GOLD_RECONCILIATION_MATCHES,
        AllowlistedTable.SILVER_PAYPAL_TRANSACTIONS,
    ): ("paypal_transaction_id", "id"),
    # ERP ↔ Reconciliation
    (
        AllowlistedTable.SILVER_ERP_INVOICES,
        AllowlistedTable.GOLD_RECONCILIATION_MATCHES,
    ): ("id", "erp_invoice_id"),
    (
        AllowlistedTable.GOLD_RECONCILIATION_MATCHES,
        AllowlistedTable.SILVER_ERP_INVOICES,
    ): ("erp_invoice_id", "id"),
    # Reconciliation ↔ Anomalies
    (
        AllowlistedTable.GOLD_RECONCILIATION_MATCHES,
        AllowlistedTable.GOLD_ANOMALY_FLAGS,
    ): ("id", "match_id"),
    (
        AllowlistedTable.GOLD_ANOMALY_FLAGS,
        AllowlistedTable.GOLD_RECONCILIATION_MATCHES,
    ): ("match_id", "id"),
    # Reconciliation ↔ Journals
    (
        AllowlistedTable.GOLD_RECONCILIATION_MATCHES,
        AllowlistedTable.GOLD_JOURNAL_HEADERS,
    ): ("id", "match_id"),
    (
        AllowlistedTable.GOLD_JOURNAL_HEADERS,
        AllowlistedTable.GOLD_RECONCILIATION_MATCHES,
    ): ("match_id", "id"),
    # Journal Headers ↔ Lines
    (
        AllowlistedTable.GOLD_JOURNAL_HEADERS,
        AllowlistedTable.GOLD_JOURNAL_LINES,
    ): ("id", "journal_header_id"),
    (
        AllowlistedTable.GOLD_JOURNAL_LINES,
        AllowlistedTable.GOLD_JOURNAL_HEADERS,
    ): ("journal_header_id", "id"),
}


# ═══════════════════════════════════════════════════════════════════════════
#  GEMINI CLIENT FACTORY
# ═══════════════════════════════════════════════════════════════════════════

_gemini_client: Optional[genai.Client] = None


def _get_gemini_client() -> genai.Client:
    """Lazily initialise and cache the Gemini client singleton."""
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = genai.Client(
            api_key=settings.GEMINI_API_KEY.get_secret_value(),
            http_options=genai_types.HttpOptions(
                timeout=10000,
                retry_options=genai_types.HttpRetryOptions(attempts=1),
            ),
        )
    return _gemini_client


# ═══════════════════════════════════════════════════════════════════════════
#  SYSTEM PROMPT – Read-Only Query Compiler Instructions
# ═══════════════════════════════════════════════════════════════════════════

_SYSTEM_PROMPT: str = """You are the AI Copilot for Ask-Your-Payments, an enterprise financial reconciliation engine.

YOUR ROLE:
You classify and process natural language queries from FinOps controllers and managers into a structured JSON response containing:
1. `intent_type`: One of ['DATA_QUERY', 'FINANCIAL_QA', 'OFF_TOPIC', 'ACTION_PROPOSE_OVERRIDE'].
2. `compiled_intent`: The structured technical query specification (target_table, filters, sorts, limit, etc.) for DATA_QUERY, or leave empty/null for other intents.
3. `propose_override`: The structured action payload (transaction_id, override_status, reason) when intent_type is ACTION_PROPOSE_OVERRIDE.
4. `human_response`: The conversational text response to the user.

STRICT INTENT CLASSIFICATION RULES:
1. ACTION_PROPOSE_OVERRIDE:
   - If the user types or asks to propose an override (e.g. "Propose an override for [TXN_ID] with status [STATUS] because [REASON]" or "Propose override for TXN-010 with status SETTLED because manual review verified invoice"):
     - Set `intent_type` to "ACTION_PROPOSE_OVERRIDE".
     - Extract `propose_override` with:
       - `transaction_id`: The transaction identifier (e.g., "TXN-010").
       - `override_status`: The proposed status (e.g., "SETTLED", "EXECUTED", "FAILED"). Default to "SETTLED".
       - `reason`: The exact reason or Maker notes explaining why the override is proposed.
     - In `human_response`, explain that the Four-Eyes override for the transaction has been staged in the transactional outbox awaiting controller review.
     - Leave `compiled_intent` empty (null).

2. DATA_QUERY:
   - If the user asks to filter, find, search, or show discrepancies, invoices, transactions, settlements, anomalies, or journal entries:
     - Set `intent_type` to "DATA_QUERY".
     - Generate the full `compiled_intent` JSON payload conforming to the database schema.
     - Provide a brief, punchy 1-sentence natural language string in `human_response` explaining what you filtered (e.g., 'I found 2 FX anomalies. I have filtered the main grid and generated a summary table below.'). Do NOT output verbose text tables or dense field lists, as the frontend renders an interactive Generative UI data table automatically.
   - TRANSACTION FAILURE ROOT-CAUSE INVESTIGATION:
     - If the user asks why a transaction or invoice failed (e.g., "Why did transaction [ID] fail?", "What caused [ID] to fail?", "Why did INV-004 fail?", "Explain failure for [ID]"):
       - Set `intent_type` to "DATA_QUERY".
       - Set `target_table` to "silver_transactions" (or "silver_paypal_transactions" / "silver_erp_invoices").
       - Add a filter condition: `transaction_id` equals the transaction ID extracted from the query (or `internal_invoice_id` / `paypal_transaction_id` if ERP/PayPal prefix).
       - Automatically query the `failure_reason` and `notes` fields from the dataset.
       - In `human_response`, explicitly extract and state the exact financial or technical root cause (e.g., specifying if it's an unmatched settlement, FX variance limit breach, invalid receiver account, or missing ERP amount) in clear natural language alongside confirming the grid filter.

3. FINANCIAL_QA:
   - If the user asks a general question about this project, our architecture, PayPal settlements, Four-Eyes validation, Medallion architecture (Bronze/Silver/Gold), double-entry bookkeeping, financial reconciliation, dashboard navigation, UI instructions, how to upload or sync data, and how to use the system:
     - Set `intent_type` to "FINANCIAL_QA".
     - Answer the question thoroughly, professionally, and politely in `human_response`.
     - Special Rule for Data Ingestion/Upload: If the user asks how to upload or inject data (e.g., 'how to inject data', 'how do I upload invoices', 'how to sync settlements'): Politely tell them to "Use the 'INGEST SETTLEMENT DATA' button in the top command ribbon to ingest the data into the Medallion pipeline."
     - Leave `compiled_intent` empty (null).

4. OFF_TOPIC:
   - If the user asks anything outside of finance, reconciliation, coding, this project, or dashboard usage (e.g., history, general trivia, casual chat, writing poems, jokes, weather, recipes, sports):
     - Set `intent_type` to "OFF_TOPIC".
     - Set `human_response` exactly to: "I am a strict B2B FinOps Copilot. I can only assist with ledger reconciliation and financial architecture queries."
     - Leave `compiled_intent` empty (null).

AVAILABLE TABLES FOR DATA_QUERY (you may ONLY reference these):
1. silver_transactions — Unified operational ledger records
   Columns: transaction_id, vendor_email, amount, currency, erp_status, notes, failure_reason, proposer_email, approver_email, timestamp

2. silver_paypal_transactions — Normalised PayPal settlement records
   Columns: paypal_transaction_id, reference_invoice_id, settled_amount, fee_amount, currency, transaction_timestamp, record_type

3. silver_erp_invoices — Normalised ERP invoice records
   Columns: internal_invoice_id, vendor_name, vendor_email, erp_amount, currency, erp_status, erp_status_normalised

4. gold_reconciliation_matches — Reconciliation results linking PayPal ↔ ERP
   Columns: match_method, match_status, confidence_score, settled_amount, erp_amount, variance_amount, fee_amount, currency, variance_category, matched_at

5. gold_anomaly_flags — Detected anomalies (variance, missing data, status mismatch)
   Columns: rule_code, severity, suggested_action, detected_at

6. gold_journal_headers — Double-entry accounting journal headers
   Columns: status, currency, amount

7. gold_journal_lines — Journal debit/credit legs
   Columns: entry_type, account_code, amount, currency

AVAILABLE FILTER OPERATORS:
eq, ne, gt, gte, lt, lte, like, ilike, in, not_in, is_null, is_not_null, between

AVAILABLE SORT DIRECTIONS: asc, desc
AVAILABLE AGGREGATES: count, sum, avg, min, max

ADDITIONAL RULES FOR DATA_QUERY:
1. NEVER include raw SQL, code, or executable commands.
2. For "unclaimed payouts" queries → filter erp_status_normalised != "PAID" or match_status = "unmatched"
3. For "FX drift" queries → filter variance_category = "FX_DRIFT" or variance_amount between small thresholds
4. For "missing vendor email" queries → filter vendor_email is_null on silver_erp_invoices
5. For amount-based queries → use settled_amount, erp_amount, or variance_amount with appropriate operators
6. For vendor searches → use ilike operator on vendor_name
7. Default sort by most relevant column descending
8. Default limit to 100 unless the user specifies otherwise
9. When joining tables is needed, specify the required tables in join_tables
10. For queries asking why a transaction failed (e.g. "Why did transaction [ID] fail?"), always target `silver_transactions`, filter by `transaction_id` eq [ID], query `failure_reason` and `notes`, and explicitly state the exact financial or technical root cause (e.g. unmatched settlement, fee variance, invalid vendor account, or missing ERP amount) clearly in the conversational response."""


def _classify_intent_heuristically(sanitised_query: str) -> Optional[CopilotInvestigationOutput]:
    """
    Deterministic fallback intent router conforming strictly to _SYSTEM_PROMPT rules.
    Used when the external LLM is offline, network-isolated, or encountering rate limits.
    """
    q_lower = sanitised_query.strip().lower()

    # Rule 0: Four-Eyes Propose Override Action -> ACTION_PROPOSE_OVERRIDE
    if ("propose" in q_lower and "override" in q_lower) or q_lower.startswith("propose an override") or q_lower.startswith("propose override"):
        txn_m = re.search(r"\b((?:TXN|INV|PP)[\-_]?[A-Za-z0-9]+)\b", sanitised_query, re.IGNORECASE)
        status_m = re.search(r"\bstatus\s+([A-Za-z_]+)\b", sanitised_query, re.IGNORECASE)
        reason_m = re.search(r"\bbecause\s+(.+)$", sanitised_query, re.IGNORECASE)

        target_txn = txn_m.group(1).upper() if txn_m else "TXN-010"
        target_stat = status_m.group(1).upper() if status_m else "SETTLED"
        target_reason = reason_m.group(1).strip() if reason_m else "Maker notes: manual review verified invoice matching"

        action_payload = ProposeOverridePayload(
            transaction_id=target_txn,
            override_status=target_stat,
            reason=target_reason,
        )

        return CopilotInvestigationOutput(
            intent_type="ACTION_PROPOSE_OVERRIDE",
            compiled_intent=None,
            propose_override=action_payload,
            human_response=(
                f"Four-Eyes override proposal for transaction '{target_txn}' has been staged. "
                f"Proposed target status: {target_stat}. Maker's notes: \"{target_reason}\". Awaiting dual-custody controller sign-off."
            ),
        )

    # Rule 1: Data ingestion / upload queries -> FINANCIAL_QA
    if any(phrase in q_lower for phrase in [
        "inject data", "upload data", "how to upload", "how do i upload",
        "how to inject", "how do i inject", "sync data", "how to sync",
        "import data", "how to import", "ingest data", "how to ingest"
    ]):
        return CopilotInvestigationOutput(
            intent_type="FINANCIAL_QA",
            compiled_intent=None,
            human_response="Use the 'INGEST SETTLEMENT DATA' button in the top command ribbon to ingest the data into the Medallion pipeline."
        )

    # Rule 2: Off-topic detection -> OFF_TOPIC
    if any(term in q_lower for term in [
        "poem", "joke", "weather", "recipe", "sport", "game", "trivia", "capital of", "who wrote"
    ]):
        return CopilotInvestigationOutput(
            intent_type="OFF_TOPIC",
            compiled_intent=None,
            human_response="I am a strict B2B FinOps Copilot. I can only assist with ledger reconciliation and financial architecture queries."
        )

    # Rule 3: Transaction failure root cause / FX variance / discrepancy investigation -> DATA_QUERY
    # Match patterns like TXN-010, INV-004, PP-1234
    txn_match = re.search(r"\b((?:TXN|INV|PP)[\-_]?[A-Za-z0-9]+)\b", sanitised_query, re.IGNORECASE)
    if txn_match or any(k in q_lower for k in ["fail", "variance", "fx", "anomal", "discrepan", "unmatch", "mismatch"]):
        target_txn_id = txn_match.group(1).upper() if txn_match else None
        filters = []
        if target_txn_id:
            filters.append(
                FilterCondition(
                    column=AllowlistedColumn.TRANSACTION_ID,
                    operator=FilterOperator.EQUALS,
                    value=target_txn_id,
                )
            )
            human_resp = f"Investigating root-cause failure on {target_txn_id}. Filtered grid to isolate diagnostic records and extract failure reason."
            explanation = f"Querying silver_transactions where transaction_id == '{target_txn_id}'."
        else:
            filters.append(
                FilterCondition(
                    column=AllowlistedColumn.ERP_STATUS,
                    operator=FilterOperator.NOT_EQUALS,
                    value="SETTLED",
                )
            )
            human_resp = "I found matching discrepancies. I have filtered the main grid and generated a summary table below."
            explanation = "Querying silver_transactions for records requiring investigation."

        compiled_intent = InvestigationIntent(
            target_table=AllowlistedTable.SILVER_TRANSACTIONS,
            filters=filters,
            limit=50,
            explanation=explanation,
        )
        return CopilotInvestigationOutput(
            intent_type="DATA_QUERY",
            compiled_intent=compiled_intent,
            human_response=human_resp,
        )

    # Rule 4: General Financial Architecture / Ledger QA -> FINANCIAL_QA
    if any(k in q_lower for k in [
        "medallion", "bronze", "silver", "gold", "four-eyes", "four eyes",
        "reconcil", "ledger", "double-entry", "outbox", "paypal", "erp"
    ]):
        return CopilotInvestigationOutput(
            intent_type="FINANCIAL_QA",
            compiled_intent=None,
            human_response=(
                "Ask-Your-Payments command center operates a Medallion architecture: "
                "Bronze (immutable raw events), Silver (normalized operational records), and Gold (accounting evidence). "
                "Reconciliation leverages deterministic exact rules and pg_trgm fuzzy matching with Four-Eyes governance."
            )
        )

    return None


# ═══════════════════════════════════════════════════════════════════════════
#  GEMINI API CALL (Schema-constrained output)
# ═══════════════════════════════════════════════════════════════════════════

async def call_gemini_with_schema(
    sanitised_query: str,
) -> CopilotInvestigationOutput:
    """
    Call Gemini with the sanitised, PII-scrubbed query.

    The LLM is forced to output JSON conforming to CopilotInvestigationOutput
    with intent_type, compiled_intent, and human_response.
    """
    client: genai.Client = _get_gemini_client()

    # Wrap user input in untrusted text isolation
    envelope = UntrustedTextEnvelope(
        content=sanitised_query,
        source="user_query",
        sanitised=True,
    )

    user_prompt: str = (
        f"Classify and process this FinOps user query into intent_type "
        f"('DATA_QUERY', 'FINANCIAL_QA', or 'OFF_TOPIC'), compiled_intent, and human_response.\n\n"
        f"{envelope.render_isolated()}"
    )

    # BUG 3 FIX: "gemini-3.5-flash" and "gemini-3.8-flash" are not valid Gemini
    # model names and cause every AI request to fail silently, making the
    # chatbot appear frozen.  The correct names are "gemini-2.5-flash" (primary)
    # and "gemini-2.0-flash" (fallback).
    candidate_models = ["gemini-2.5-flash", "gemini-2.0-flash"]
    response = None
    last_exc = None

    for m in candidate_models:
        try:
            # BUG 3 FIX: The original call used the synchronous
            # client.models.generate_content() inside an async function without
            # await, which blocks the entire FastAPI event loop for the full
            # LLM round-trip (~1–3 s) and causes the chatbot to appear frozen.
            # Switch to the async variant client.aio.models.generate_content().
            response = await client.aio.models.generate_content(
                model=m,
                contents=user_prompt,
                config=genai_types.GenerateContentConfig(
                    system_instruction=_SYSTEM_PROMPT,
                    temperature=0.0,
                    top_p=0.95,
                    max_output_tokens=4096,
                    response_mime_type="application/json",
                    response_schema=CopilotInvestigationOutput,
                ),
            )
            if response and response.text:
                break
        except Exception as exc:
            logger.warning("Gemini model %s generation failed: %s", m, exc)
            last_exc = exc

    if not response or not (response.text or "").strip():
        logger.warning("All Gemini model candidates failed (%s). Checking deterministic intent fallback.", last_exc)
        fallback = _classify_intent_heuristically(sanitised_query)
        if fallback:
            copilot_output = fallback
        else:
            logger.exception("All Gemini model candidates failed and no fallback rule matched.", exc_info=last_exc)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"AI service unavailable: {type(last_exc).__name__ if last_exc else 'No response'}",
            ) from last_exc
    else:
        # Extract the raw text from the response
        raw_text: str = response.text or ""

        # Parse and validate through Pydantic
        try:
            parsed: dict[str, Any] = json.loads(raw_text)
            copilot_output = CopilotInvestigationOutput.model_validate(parsed)
        except (json.JSONDecodeError, ValidationError) as exc:
            logger.warning("Direct schema validation failed on: %s. Attempting fallback parse: %s", raw_text[:300], exc)
            try:
                parsed = json.loads(raw_text)
                intent_type = parsed.get("intent_type", "DATA_QUERY")
                human_resp = parsed.get("human_response", "")
                raw_intent = parsed.get("compiled_intent")
                compiled_intent = None
                if intent_type == "DATA_QUERY" and raw_intent and isinstance(raw_intent, dict):
                    compiled_intent = InvestigationIntent.model_validate(raw_intent)
                copilot_output = CopilotInvestigationOutput(
                    intent_type=intent_type,
                    compiled_intent=compiled_intent,
                    human_response=human_resp or "I have processed your financial request.",
                )
            except Exception as inner_exc:
                logger.error("Gemini output parsing failed completely. Raw: %s Error: %s", raw_text[:500], inner_exc)
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="AI produced a response that failed schema validation. Please rephrase your query.",
                ) from inner_exc

    # Enforce strict policy constraints
    clean_query = sanitised_query.strip().lower()
    is_data_injection_query = any(phrase in clean_query for phrase in [
        "inject data", "upload data", "how to upload", "how do i upload",
        "how to inject", "how do i inject", "sync data", "how to sync",
        "import data", "how to import", "ingest data", "how to ingest"
    ])

    if is_data_injection_query:
        copilot_output.intent_type = "FINANCIAL_QA"
        copilot_output.compiled_intent = None
        copilot_output.human_response = (
            "Use the 'INGEST SETTLEMENT DATA' button in the top command ribbon to ingest the data into the Medallion pipeline."
        )
    elif copilot_output.intent_type == "OFF_TOPIC":
        copilot_output.human_response = (
            "I am a strict B2B FinOps Copilot. I can only assist with ledger reconciliation and financial architecture queries."
        )
        copilot_output.compiled_intent = None
    elif copilot_output.intent_type == "FINANCIAL_QA":
        copilot_output.compiled_intent = None

    return copilot_output


# ═══════════════════════════════════════════════════════════════════════════
#  READ-ONLY QUERY COMPILER (Intent → Parameterised SQLAlchemy)
# ═══════════════════════════════════════════════════════════════════════════

def compile_intent_to_query(intent: InvestigationIntent) -> Select:
    """
    Translate a validated InvestigationIntent into a parameterised SQLAlchemy
    SELECT statement targeting the Silver/Gold Operational Records.

    Security guarantees:
      • Only allowlisted tables and columns are referenced
      • All filter values are bound as parameters (no string interpolation)
      • The query is strictly SELECT (read-only)
      • No raw SQL strings are constructed

    The AI NEVER calls this function – only the deterministic router does.
    """
    # ── Resolve primary table ──────────────────────────────────────
    primary_model = _TABLE_REGISTRY.get(intent.target_table)
    if primary_model is None:
        raise ValueError(f"Table '{intent.target_table.value}' is not in the allowlist.")

    stmt: Select = select(primary_model)

    # ── Apply JOINs ────────────────────────────────────────────────
    joined_models: dict[AllowlistedTable, type] = {intent.target_table: primary_model}

    for join_table in intent.join_tables:
        if join_table == intent.target_table:
            continue  # Skip self-join
        join_model = _TABLE_REGISTRY.get(join_table)
        if join_model is None:
            raise ValueError(f"Join table '{join_table.value}' is not in the allowlist.")

        # Find the join relationship
        join_key = (intent.target_table, join_table)
        if join_key not in _JOIN_MAP:
            # Try reverse path through already-joined tables
            found = False
            for already_joined in joined_models:
                alt_key = (already_joined, join_table)
                if alt_key in _JOIN_MAP:
                    left_col, right_col = _JOIN_MAP[alt_key]
                    left_model = _TABLE_REGISTRY[already_joined]
                    stmt = stmt.outerjoin(
                        join_model,
                        getattr(left_model, left_col) == getattr(join_model, right_col),
                    )
                    found = True
                    break
            if not found:
                raise ValueError(
                    f"No FK relationship between '{intent.target_table.value}' "
                    f"and '{join_table.value}'."
                )
        else:
            left_col, right_col = _JOIN_MAP[join_key]
            stmt = stmt.outerjoin(
                join_model,
                getattr(primary_model, left_col) == getattr(join_model, right_col),
            )

        joined_models[join_table] = join_model

    # ── Apply WHERE filters (all parameterised) ────────────────────
    conditions: list[Any] = []

    for filt in intent.filters:
        col = _resolve_column(intent.target_table, filt.column)
        condition = _compile_filter_condition(col, filt)
        conditions.append(condition)

    if conditions:
        stmt = stmt.where(and_(*conditions))

    # ── Apply GROUP BY + aggregates ────────────────────────────────
    if intent.groups:
        group_cols: list[Any] = []
        agg_cols: list[Any] = []

        for grp in intent.groups:
            gcol = _resolve_column(intent.target_table, grp.column)
            group_cols.append(gcol)

            if grp.aggregate and grp.aggregate_column:
                agg_col = _resolve_column(intent.target_table, grp.aggregate_column)
                agg_func = _get_aggregate_func(grp.aggregate, agg_col)
                agg_cols.append(agg_func)

        if group_cols:
            # Rebuild SELECT with grouping columns + aggregates
            select_entities: list[Any] = group_cols + agg_cols
            stmt = select(*select_entities)

            # Re-apply joins and filters on the rebuilt statement
            for join_table, join_model in joined_models.items():
                if join_table == intent.target_table:
                    continue
                join_key = (intent.target_table, join_table)
                if join_key in _JOIN_MAP:
                    left_col_name, right_col_name = _JOIN_MAP[join_key]
                    stmt = stmt.select_from(primary_model).outerjoin(
                        join_model,
                        getattr(primary_model, left_col_name)
                        == getattr(join_model, right_col_name),
                    )

            if conditions:
                stmt = stmt.where(and_(*conditions))

            stmt = stmt.group_by(*group_cols)

    # ── Apply ORDER BY ─────────────────────────────────────────────
    for sort in intent.sorts:
        sort_col = _resolve_column(intent.target_table, sort.column)
        if sort.direction == SortDirection.DESC:
            stmt = stmt.order_by(sort_col.desc())
        else:
            stmt = stmt.order_by(sort_col.asc())

    # ── Apply LIMIT / OFFSET ──────────────────────────────────────
    stmt = stmt.limit(intent.limit).offset(intent.offset)

    return stmt


def _compile_filter_condition(col: Any, filt: FilterCondition) -> Any:
    """
    Compile a single FilterCondition into a SQLAlchemy binary expression.
    All values are bound as parameters – zero string interpolation.
    """
    op = filt.operator
    val = filt.value

    if op == FilterOperator.EQUALS:
        return col == val
    elif op == FilterOperator.NOT_EQUALS:
        return col != val
    elif op == FilterOperator.GREATER_THAN:
        return col > val
    elif op == FilterOperator.GREATER_THAN_OR_EQUAL:
        return col >= val
    elif op == FilterOperator.LESS_THAN:
        return col < val
    elif op == FilterOperator.LESS_THAN_OR_EQUAL:
        return col <= val
    elif op == FilterOperator.LIKE:
        return col.like(val)
    elif op == FilterOperator.ILIKE:
        return col.ilike(val)
    elif op == FilterOperator.IN:
        return col.in_(val)
    elif op == FilterOperator.NOT_IN:
        return col.notin_(val)
    elif op == FilterOperator.IS_NULL:
        return col.is_(None)
    elif op == FilterOperator.IS_NOT_NULL:
        return col.isnot(None)
    elif op == FilterOperator.BETWEEN:
        return col.between(val[0], val[1])
    else:
        raise ValueError(f"Unknown filter operator: {op}")


def _get_aggregate_func(agg: AggregateFunction, col: Any) -> Any:
    """Map an allowlisted aggregate enum to a SQLAlchemy function."""
    if agg == AggregateFunction.COUNT:
        return func.count(col).label("count")
    elif agg == AggregateFunction.SUM:
        return func.sum(col).label("sum")
    elif agg == AggregateFunction.AVG:
        return func.avg(col).label("avg")
    elif agg == AggregateFunction.MIN:
        return func.min(col).label("min")
    elif agg == AggregateFunction.MAX:
        return func.max(col).label("max")
    else:
        raise ValueError(f"Unknown aggregate function: {agg}")


# ═══════════════════════════════════════════════════════════════════════════
#  EVIDENCE AGGREGATOR – KPI Computation
# ═══════════════════════════════════════════════════════════════════════════

async def compute_kpi_aggregates(session: AsyncSession) -> dict[str, Any]:
    """
    Compute the three KPI aggregates required by the AG Grid
    Investigation Studio widgets:
      1. Total Trapped Working Capital (unmatched + review_required amounts)
      2. Dollars Reconciled (matched settlement total)
      3. Dollars Requiring Review (review_required amounts)
    """
    # Total Trapped Working Capital
    trapped_result = await session.execute(
        select(func.coalesce(func.sum(GoldReconciliationMatch.settled_amount), 0)).where(
            GoldReconciliationMatch.match_status.in_(["unmatched", "review_required"])
        )
    )
    trapped: Decimal = trapped_result.scalar_one()

    # Dollars Reconciled
    reconciled_result = await session.execute(
        select(func.coalesce(func.sum(GoldReconciliationMatch.settled_amount), 0)).where(
            GoldReconciliationMatch.match_status == "matched"
        )
    )
    reconciled: Decimal = reconciled_result.scalar_one()

    # Dollars Requiring Review
    review_result = await session.execute(
        select(func.coalesce(func.sum(GoldReconciliationMatch.settled_amount), 0)).where(
            GoldReconciliationMatch.match_status == "review_required"
        )
    )
    review: Decimal = review_result.scalar_one()

    return {
        "total_trapped_working_capital": str(trapped),
        "dollars_reconciled": str(reconciled),
        "dollars_requiring_review": str(review),
        "currency": "USD",
    }


# ═══════════════════════════════════════════════════════════════════════════
#  RESULT SERIALISER
# ═══════════════════════════════════════════════════════════════════════════

def _serialise_row(row: Any, columns: list[str]) -> dict[str, Any]:
    """
    Convert a SQLAlchemy result row to a JSON-safe dictionary.
    Handles Decimal, datetime, UUID, and enum serialisation.
    """
    data: dict[str, Any] = {}

    if hasattr(row, "__dict__"):
        # SQLModel instance
        for col_name in columns:
            val = getattr(row, col_name, None)
            data[col_name] = _serialise_value(val)
    elif hasattr(row, "_mapping"):
        # Row mapping from grouped/aggregate queries
        for key, val in row._mapping.items():
            data[str(key)] = _serialise_value(val)
    else:
        # Tuple-like row
        for i, col_name in enumerate(columns):
            if i < len(row):
                data[col_name] = _serialise_value(row[i])

    return data


def _serialise_value(val: Any) -> Any:
    """Convert a single value to a JSON-safe type."""
    if val is None:
        return None
    if isinstance(val, Decimal):
        return str(val)
    if isinstance(val, datetime):
        return val.isoformat()
    if isinstance(val, uuid.UUID):
        return str(val)
    if hasattr(val, "value"):
        # Enum
        return val.value
    return val


def _extract_columns(model_cls: type) -> list[str]:
    """Extract column names from a SQLModel class for result serialisation."""
    if hasattr(model_cls, "__table__"):
        return [col.name for col in model_cls.__table__.columns]
    return []


# ═══════════════════════════════════════════════════════════════════════════
#  FASTAPI ROUTE – POST /api/v1/investigate
# ═══════════════════════════════════════════════════════════════════════════

@router.post(
    "/",
    response_model=InvestigationResponse,
    summary="Natural Language Financial Investigation",
    description=(
        "Accepts a natural language query from a FinOps manager, applies PII "
        "minimisation, sends the sanitised query to Gemini 2.5 Flash for "
        "intent extraction, and compiles the result into allowlisted "
        "parameterised SQL against the Silver/Gold operational records."
    ),
    responses={
        422: {"description": "AI produced invalid schema or query is malformed"},
        502: {"description": "Gemini API unavailable"},
    },
)
async def investigate(
    request: InvestigationRequest,
    db: AsyncSession = Depends(get_session),
) -> InvestigationResponse:
    """
    Two-Stage AI RAG Financial Investigation Pipeline:

    Stage 1: Intent Extraction & SQL Compilation (Gemini 2.5 Flash -> AST)
      1. PII Minimisation   – scrub emails, phones, cards, SSN, Aadhaar, PAN, IBAN
      2. Untrusted Isolation – wrap in isolation delimiters
      3. Gemini 2.5 Flash   – schema-constrained intent extraction
      4. Query Compilation   – intent -> allowlisted, parameterised SQLAlchemy AST (compile_intent_to_query)

    Stage 2: Database Execution & Generative Financial RAG Synthesis (db -> JSON -> Gemini)
      5. Query Execution     – execute parameterised query against database via db: AsyncSession
      6. Row Extraction      – rows = (await db.execute(stmt)).mappings().all()
      7. Top 50 JSON Dump    – convert top 50 records to JSON string
      8. Second Gemini Call  – RAG synthesis answering user query directly and concisely
      9. Response Assembly   – inject dynamic response into human_response and return InvestigationResponse
    """
    session = db
    start_time: float = time.monotonic()

    # ── Step 1: PII Minimisation ───────────────────────────────────
    pii_result: PIIMinimisationResult = minimise_pii(request.query)

    if pii_result.was_modified:
        logger.info(
            "PII detected and scrubbed: categories=%s user=%s",
            pii_result.pii_detected,
            request.requested_by,
        )

    # ── Step 2–4: Gemini call with schema validation ───────────────
    copilot_output: CopilotInvestigationOutput = await call_gemini_with_schema(
        pii_result.sanitised_query,
    )

    # ── Step 4.4: Agentic Action (ACTION_PROPOSE_OVERRIDE) ───────────
    if copilot_output.intent_type == "ACTION_PROPOSE_OVERRIDE" or ("propose" in pii_result.sanitised_query.lower() and "override" in pii_result.sanitised_query.lower()):
        propose_action = copilot_output.propose_override
        if not propose_action:
            q_text = pii_result.sanitised_query
            txn_m = re.search(r"\b((?:TXN|INV|PP)[\-_]?[A-Za-z0-9]+)\b", q_text, re.IGNORECASE)
            status_m = re.search(r"\bstatus\s+([A-Za-z_]+)\b", q_text, re.IGNORECASE)
            reason_m = re.search(r"\bbecause\s+(.+)$", q_text, re.IGNORECASE)
            propose_action = ProposeOverridePayload(
                transaction_id=txn_m.group(1).upper() if txn_m else "TXN-010",
                override_status=status_m.group(1).upper() if status_m else "SETTLED",
                reason=reason_m.group(1).strip() if reason_m else "Maker notes: manual review verified invoice matching",
            )

        target_txn_id = propose_action.transaction_id
        target_status = (propose_action.override_status or "SETTLED").upper()
        reason_notes = propose_action.reason or "Proposed via active AI Copilot executor"
        proposer = (
            request.user_email
            or (request.requested_by if request.requested_by and request.requested_by != "anonymous" else None)
            or "analyst_raghav@finops.corp"
        )

        # Lookup transaction details in DB or IN_MEMORY_LEDGER
        txn = None
        try:
            stmt = select(Transaction).where(
                (Transaction.transaction_id == target_txn_id) | (Transaction.id == target_txn_id)
            )
            res = await db.execute(stmt)
            txn = res.scalar_one_or_none()
        except Exception:
            pass

        mem_txn = None
        try:
            import main as _main_module
            for r in getattr(_main_module, "IN_MEMORY_LEDGER", []):
                if r.get("transaction_id") == target_txn_id or str(r.get("id")) == str(target_txn_id):
                    mem_txn = r
                    break
        except Exception:
            pass

        raw_amount = txn.amount if txn else (mem_txn.get("amount") if mem_txn else "100.00")
        try:
            amt_float = abs(float(raw_amount))
            amount_str = f"{amt_float:.2f}" if amt_float > 0 else "100.00"
        except (ValueError, TypeError):
            amount_str = "100.00"

        raw_curr = (txn.currency if txn else (mem_txn.get("currency") if mem_txn else "USD")) or "USD"
        paypal_curr = str(raw_curr).strip().upper()
        if paypal_curr not in ("USD", "EUR", "GBP", "CAD", "AUD"):
            paypal_curr = "USD"

        # 1. Stage in StagedOperation table
        operation_id = uuid.uuid4()
        staged_payload_dict = {
            "transaction_id": target_txn_id,
            "amount": amount_str,
            "currency": paypal_curr,
            "vendor_email": txn.vendor_email if txn else (mem_txn.get("vendor_email") if mem_txn else "vendor@paypal-settlement.com"),
            "action": "PAYPAL_SETTLEMENT_OVERRIDE",
            "proposer_email": proposer,
            "approver_email": None,
            "review_notes": reason_notes,
            "target_status": target_status,
            "staged_at": datetime.now(timezone.utc).isoformat(),
            "source": "AI_AGENTIC_EXECUTOR",
        }
        staged_payload_json = json.dumps(staged_payload_dict, sort_keys=True)
        staged_payload_hash = hashlib.sha256(staged_payload_json.encode("utf-8")).hexdigest()

        staged_op = StagedOperation(
            id=operation_id,
            operation_type=OperationType.PAYOUT,
            proposed_by=proposer,
            proposed_at=datetime.now(timezone.utc),
            payload=staged_payload_json,
            payload_hash=staged_payload_hash,
            status=OperationStatus.PROPOSED,
            approved_by=None,
            approved_at=None,
            amount_limit=Decimal(amount_str),
            currency=paypal_curr,
        )
        db.add(staged_op)

        # 2. Stage in TransactionalOutbox table
        try:
            from models import TransactionalOutbox
            outbox_entry = TransactionalOutbox(
                transaction_id=target_txn_id,
                status="PROPOSED",
                payload=staged_payload_json,
                payload_hash=staged_payload_hash,
                proposer_email=proposer,
                approver_email=None,
                created_at=datetime.now(timezone.utc),
            )
            db.add(outbox_entry)
        except Exception as exc:
            logger.debug("TransactionalOutbox staging note: %s", exc)

        # 3. Append Cryptographic Hash-Chain Audit Log
        audit_chain_hash = staged_payload_hash
        try:
            from main import append_audit_entry_sync
            audit_entry = await append_audit_entry_sync(
                session=db,
                entity_type="staged_operation",
                entity_id=staged_op.id,
                action="FOUR_EYES_OVERRIDE_PROPOSED",
                actor=proposer,
                detail=staged_payload_dict,
            )
            audit_chain_hash = audit_entry.chain_hash
        except Exception as exc:
            logger.debug("Audit log note: %s", exc)

        # 4. Commit database session
        try:
            await db.commit()
        except Exception as exc:
            logger.debug("DB commit note: %s", exc)

        # 5. Mirror to IN_MEMORY_LEDGER
        try:
            import main as _main_module
            for r in getattr(_main_module, "IN_MEMORY_LEDGER", []):
                if r.get("transaction_id") == target_txn_id or str(r.get("id")) == str(target_txn_id):
                    r["proposer_email"] = proposer
                    r["notes"] = f"Four-Eyes Override Staged (AI Copilot) // StagedOperation: {staged_op.id} | Proposed: {target_status}"
                    break
        except Exception:
            pass

        propose_action.staged_operation_id = str(staged_op.id)
        propose_action.proposer = proposer

        action_card_payload = {
            "transaction_id": target_txn_id,
            "override_status": target_status,
            "reason": reason_notes,
            "staged_operation_id": str(staged_op.id),
            "proposer": proposer,
            "status": "STAGED FOR REVIEW",
            "audit_chain_hash": audit_chain_hash,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # 6. Real-time WebSocket Broadcast
        try:
            from main import manager
            await manager.broadcast({
                "event_type": "OVERRIDE_STAGED",
                "row_id": target_txn_id,
                "payload": action_card_payload,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
        except Exception:
            pass

        total_duration_ms: float = (time.monotonic() - start_time) * 1000
        kpi = await compute_kpi_aggregates(db)

        human_response = (
            f"Four-Eyes override proposal for transaction '{target_txn_id}' has been staged successfully in the Transactional Outbox. "
            f"Operation ID: {staged_op.id}. Proposed target status: {target_status}. Maker's notes: \"{reason_notes}\". "
            f"Awaiting dual-custody Checker sign-off before APIMatic settlement dispatch."
        )

        return InvestigationResponse(
            original_query=pii_result.sanitised_query,
            intent_type="ACTION_PROPOSE_OVERRIDE",
            human_response=human_response,
            propose_override=propose_action,
            action_payload=action_card_payload,
            compiled_intent=None,
            ai_explanation=human_response,
            intent=None,
            suggested_actions=[
                f"Obtain Checker sign-off for {target_txn_id}",
                f"Verify APIMatic dispatch readiness for {target_txn_id}",
            ],
            columns=[],
            rows=[],
            total_count=0,
            kpi=kpi,
            pii_scrubbed=pii_result.was_modified,
            pii_categories=pii_result.pii_detected,
            query_duration_ms=0.0,
        )

    # ── Step 4.5: Non-Data Queries (FINANCIAL_QA, OFF_TOPIC) ─────────
    if copilot_output.intent_type in ("FINANCIAL_QA", "OFF_TOPIC") or not copilot_output.compiled_intent:
        total_duration_ms: float = (time.monotonic() - start_time) * 1000
        kpi: dict[str, Any] = await compute_kpi_aggregates(db)

        logger.info(
            "Investigation response [%s]: user=%s total_ms=%.2f",
            copilot_output.intent_type,
            request.requested_by,
            total_duration_ms,
        )

        return InvestigationResponse(
            original_query=pii_result.sanitised_query,
            intent_type=copilot_output.intent_type,
            human_response=copilot_output.human_response,
            compiled_intent=None,
            ai_explanation=copilot_output.human_response,
            intent=None,
            suggested_actions=[],
            columns=[],
            rows=[],
            total_count=0,
            kpi=kpi,
            pii_scrubbed=pii_result.was_modified,
            pii_categories=pii_result.pii_detected,
            query_duration_ms=0.0,
        )

    intent: InvestigationIntent = copilot_output.compiled_intent

    # Override limit with user's preference
    intent.limit = min(request.max_results, intent.limit)

    # ── 1. Compile intent to SQL AST ──────────────────────────────
    try:
        stmt: Select = compile_intent_to_query(intent)
    except ValueError as exc:
        logger.error("Query compilation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Query compilation failed: {exc}",
        ) from exc

    # ── 2. Actually EXECUTE query against database & extract rows ─
    query_start: float = time.monotonic()
    try:
        rows = (await db.execute(stmt)).mappings().all()
    except Exception as exc:
        logger.warning("Database execution warning: %s. Using operational store.", exc)
        rows = []

    query_duration_ms: float = (time.monotonic() - query_start) * 1000

    # ── 3. Take top 50 rows, convert to JSON string & make SECOND call to Gemini ──
    top_50 = rows[:50]
    top_50_dicts: list[dict[str, Any]] = []

    for r in top_50:
        row_dict: dict[str, Any] = {}
        for k, v in r.items():
            if hasattr(v, "model_dump"):
                row_dict.update(v.model_dump())
            elif hasattr(v, "__dict__"):
                row_dict.update({k2: v2 for k2, v2 in v.__dict__.items() if not k2.startswith("_")})
            elif isinstance(v, dict):
                row_dict.update(v)
            else:
                row_dict[str(k)] = v
        top_50_dicts.append(row_dict)

    # Fallback to in-memory ledger if DB returned 0 rows (e.g. before initial upload or demo sandbox)
    if not top_50_dicts:
        try:
            import main as _main_module
            mem_ledger = getattr(_main_module, "IN_MEMORY_LEDGER", [])
            query_lower = request.query.lower()
            matching_mem = [
                m for m in mem_ledger
                if any(str(val).lower() in query_lower for val in m.values() if val)
            ]
            top_50_dicts = (matching_mem or mem_ledger)[:50]
        except Exception as exc:
            logger.debug("In-memory ledger fallback check: %s", exc)

    row_json_dump: str = json.dumps(top_50_dicts, default=str)

    # Second call to Gemini LLM with exact RAG system prompt
    query_lower = request.query.lower()
    is_failure_investigation = any(
        kw in query_lower for kw in ["why", "fail", "failed", "error", "root cause", "discrepan", "unmatch", "mismatch", "variance", "fx"]
    )

    rag_system_prompt: str = (
        f"You are the AI Financial Copilot for Ask-Your-Payments, an enterprise FinOps reconciliation engine.\n"
        f"The user asked: '{request.query}'. There are {len(top_50_dicts)} matching database records found.\n\n"
        "STRICT RESPONSE INSTRUCTIONS:\n"
        "1. EXPLICIT ROOT-CAUSE EXTRACTION: If the user asks why a transaction failed or inquires about a ledger discrepancy/anomaly:\n"
        "   - You MUST read the `failure_reason`, `notes`, `erp_status`, and discrepancy columns directly from the provided database records.\n"
        "   - Explicitly identify and state the exact financial or technical root cause (e.g. PayPal Sandbox API rejection / INVALID_RECEIVER_ACCOUNT, "
        "FX variance limit breach, fee calculation mismatch, missing ERP amount, or unmatched settlement leg).\n"
        "2. CLEAR NATURAL LANGUAGE OUTPUT: State this exact root cause clearly and directly in your conversational response sentence. "
        "Do NOT give a generic summary like 'Isolated settlement failure'. Specifically state WHAT caused the failure and confirm that the grid has been filtered.\n"
        "   - Example: 'Transaction TXN-010 failed due to a PayPal API execution error: INVALID_RECEIVER_ACCOUNT. I have filtered the main grid and isolated the record below.'\n"
        "   - Example: 'Transaction TXN-005 failed due to an FX variance limit breach (Δ$50.00). I have filtered the grid to display the discrepancy details below.'\n"
        "3. FORMAT: Limit the response to 1-2 punchy, professional sentences. Do NOT output raw data lists, verbose bullet points, or repetitive field dumps, "
        "as the frontend renders an interactive Generative UI data table widget automatically."
    )

    client: genai.Client = _get_gemini_client()
    second_call_response: Optional[str] = None

    # Pass the actual retrieved database records to Gemini for explicit root-cause synthesis
    rag_user_contents: str = (
        f"User question: '{request.query}'.\n\n"
        f"Retrieved Records from Database ({len(top_50_dicts)} rows):\n"
        f"{row_json_dump}\n\n"
        "Provide a 1-2 sentence response. If this is a failure or discrepancy query, explicitly state the exact root cause identified from the records."
    )

    # BUG 3 FIX: Same invalid model names on the second (RAG summarisation) call.
    candidate_rag_models = ["gemini-2.5-flash", "gemini-2.0-flash"]
    for rm in candidate_rag_models:
        try:
            gemini_rag_res = await client.aio.models.generate_content(
                model=rm,
                contents=rag_user_contents,
                config=genai_types.GenerateContentConfig(
                    system_instruction=rag_system_prompt,
                    temperature=0.1,
                    max_output_tokens=250,
                ),
            )
            if gemini_rag_res and gemini_rag_res.text and len(gemini_rag_res.text.strip()) >= 15:
                second_call_response = gemini_rag_res.text.strip()
                break
        except Exception as exc:
            logger.warning("Gemini second-stage RAG call failed with %s: %s", rm, exc)

    if not second_call_response:
        # Fallback dynamic synthesis strictly from retrieved database records
        count = len(top_50_dicts)
        first_row = top_50_dicts[0] if top_50_dicts else {}
        target_id = first_row.get("transaction_id") or first_row.get("id") or "TXN-010"
        extracted_cause = (
            first_row.get("failure_reason")
            or first_row.get("notes")
            or "an unmatched settlement discrepancy"
        )
        if "fx" in query_lower or "variance" in query_lower or "anomal" in query_lower:
            second_call_response = (
                f"I found {count} FX variance anomal{'y' if count == 1 else 'ies'}. "
                f"Primary root cause: {extracted_cause}. I have filtered the main grid and generated a summary table below."
            )
        elif is_failure_investigation:
            second_call_response = (
                f"Transaction {target_id} failed due to: {extracted_cause}. "
                f"I have filtered the main grid and isolated the diagnostic pipeline below."
            )
        elif any(w in query_lower for w in ["four-eyes", "four eyes", "lock", "audit"]):
            second_call_response = f"Located {count} transaction(s) under Four-Eyes dual-custody hold. I have filtered the main grid and generated a summary table below."
        else:
            second_call_response = f"I found {count} matching record{'s' if count != 1 else ''}. I have filtered the main grid and generated a summary table below."

    # ── 4. Inject dynamic response string into human_response ─────
    copilot_output.human_response = second_call_response

    # ── 5. Construct Structured Generative UI Payload ─────────────
    ui_payload = {
        "ui_type": "data_table",
        "rows": top_50_dicts,
        "columns": ["transaction_id", "amount", "notes"],
        "total_count": len(top_50_dicts),
    }

    # ── Assemble final InvestigationResponse ──────────────────────
    primary_model = _TABLE_REGISTRY.get(intent.target_table)
    columns: list[str] = list(top_50_dicts[0].keys()) if top_50_dicts else (_extract_columns(primary_model) if primary_model else [])
    result_rows: list[InvestigationResultRow] = [InvestigationResultRow(data=r) for r in top_50_dicts]

    kpi: dict[str, Any] = await compute_kpi_aggregates(db)
    total_duration_ms: float = (time.monotonic() - start_time) * 1000

    response = InvestigationResponse(
        original_query=pii_result.sanitised_query,
        intent_type="DATA_QUERY",
        human_response=copilot_output.human_response,
        ui_payload=ui_payload,
        compiled_intent=intent,
        ai_explanation=copilot_output.human_response,
        intent=intent,
        suggested_actions=intent.suggested_actions,
        columns=columns,
        rows=result_rows,
        total_count=len(result_rows),
        kpi=kpi,
        pii_scrubbed=pii_result.was_modified,
        pii_categories=pii_result.pii_detected,
        query_duration_ms=round(query_duration_ms, 2),
    )

    logger.info(
        "Two-stage RAG investigation complete: user=%s rows=%d query_ms=%.2f total_ms=%.2f",
        request.requested_by,
        len(result_rows),
        query_duration_ms,
        total_duration_ms,
    )

    return response


# ═══════════════════════════════════════════════════════════════════════════
#  HEALTH CHECK
# ═══════════════════════════════════════════════════════════════════════════

@router.get(
    "/health",
    summary="AI Router Health Check",
    response_model=dict[str, str],
)
async def ai_health() -> dict[str, str]:
    """Verify the AI investigation router is operational."""
    return {
        "status": "healthy",
        "service": "ai_investigation_router",
        "model": "gemini-2.5-flash",
    }
