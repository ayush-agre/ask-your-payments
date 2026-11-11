/**
 * types.ts – Strict TypeScript interfaces mirroring Python backend schemas
 * =========================================================================
 * Team CrackerX · PayPal AI Hackathon 2026
 *
 * These types are the TypeScript side of the AI-to-Grid Contract.
 * Every field name maps 1:1 to the Python Pydantic models in:
 *   - models.py         (database schema enums)
 *   - ai_schema_validators.py (InvestigationResponse, KPI shapes)
 */

// ═══════════════════════════════════════════════════════════════════════════
//  BACKEND ENUM MIRRORS  (from models.py)
// ═══════════════════════════════════════════════════════════════════════════

export type MatchStatus =
  | "matched"
  | "partial"
  | "unmatched"
  | "disputed"
  | "review_required";

export type MatchMethod =
  | "deterministic_id"
  | "deterministic_rule"
  | "fuzzy_trgm"
  | "manual_review";

export type VarianceCategory =
  | "EXACT"
  | "FEE"
  | "FX_DRIFT"
  | "SIGNIFICANT";

export type AnomalySeverity = "info" | "warning" | "critical";

export type JournalStatus = "draft" | "posted" | "reversed";

export type JournalEntryType = "debit" | "credit";

export type OperationStatus =
  | "proposed"
  | "approved"
  | "rejected"
  | "executed"
  | "failed"
  | "expired";

// ═══════════════════════════════════════════════════════════════════════════
//  GOLD LAYER ROW  (gold_reconciliation_matches)
// ═══════════════════════════════════════════════════════════════════════════

export interface ReconciliationMatchRow {
  id: string;
  paypal_transaction_id: string;
  erp_invoice_id: string | null;
  match_method: MatchMethod;
  match_status: MatchStatus;
  confidence_score: string | null;    // NUMERIC comes as string from backend
  settled_amount: string;
  erp_amount: string | null;
  variance_amount: string | null;
  fee_amount: string | null;
  currency: string;
  variance_category: VarianceCategory | null;
  reviewed_by: string | null;
  reviewed_at: string | null;
  review_notes: string | null;
  matched_at: string;
}

// ═══════════════════════════════════════════════════════════════════════════
//  SILVER LAYER ROWS  (from Silver Operational Records)
// ═══════════════════════════════════════════════════════════════════════════

export interface PayPalTransactionRow {
  id: string;
  paypal_transaction_id: string;
  reference_invoice_id: string | null;
  settled_amount: string;
  fee_amount: string;
  currency: string;
  transaction_timestamp: string;
  record_type: string;
}

export interface ERPInvoiceRow {
  id: string;
  internal_invoice_id: string;
  vendor_name: string;
  vendor_email: string | null;
  erp_amount: string;
  currency: string;
  erp_status: string;
  erp_status_normalised: string | null;
}

// ═══════════════════════════════════════════════════════════════════════════
//  GOLD ANOMALY FLAGS  (lazy-loaded master-detail evidence)
// ═══════════════════════════════════════════════════════════════════════════

export interface AnomalyFlagRow {
  id: string;
  match_id: string | null;
  rule_code: string;
  severity: AnomalySeverity;
  description: string;
  suggested_action: string | null;
  detected_at: string;
  resolved_at: string | null;
  resolved_by: string | null;
}

// ═══════════════════════════════════════════════════════════════════════════
//  JOURNAL EVIDENCE  (lazy-loaded master-detail)
// ═══════════════════════════════════════════════════════════════════════════

export interface JournalLineRow {
  id: string;
  journal_header_id: string;
  entry_type: JournalEntryType;
  account_code: string;
  account_name: string;
  amount: string;
  currency: string;
  memo: string | null;
}

// ═══════════════════════════════════════════════════════════════════════════
//  MASTER-DETAIL EVIDENCE PAYLOAD  (from GET /api/v1/evidence/{match_id})
// ═══════════════════════════════════════════════════════════════════════════

export interface EvidenceDetail {
  match_id: string;
  paypal_transaction: PayPalTransactionRow | null;
  erp_invoice: ERPInvoiceRow | null;
  anomaly_flags: AnomalyFlagRow[];
  journal_lines: JournalLineRow[];
  raw_paypal_webhook_json: string | null;
  raw_erp_csv_row: string | null;
}

// ═══════════════════════════════════════════════════════════════════════════
//  KPI AGGREGATES  (from InvestigationResponse.kpi)
// ═══════════════════════════════════════════════════════════════════════════

export interface KpiAggregates {
  total_trapped_working_capital: string;
  dollars_reconciled: string;
  dollars_requiring_review: string;
  currency: string;
}

// ═══════════════════════════════════════════════════════════════════════════
//  AI INVESTIGATION RESPONSE  (from POST /api/v1/investigate/)
// ═══════════════════════════════════════════════════════════════════════════

export interface InvestigationResponse {
  investigation_id: string;
  original_query: string;
  ai_explanation: string;
  suggested_actions: string[];
  columns: string[];
  rows: Array<{ data: Record<string, unknown> }>;
  total_count: number;
  kpi: KpiAggregates;
  pii_scrubbed: boolean;
  pii_categories: string[];
  executed_at: string;
  query_duration_ms: number | null;
}

// ═══════════════════════════════════════════════════════════════════════════
//  SSRM REQUEST / RESPONSE  (AG Grid Server-Side Row Model contract)
// ═══════════════════════════════════════════════════════════════════════════

export interface SSRMRequest {
  startRow: number;
  endRow: number;
  sortModel: Array<{ colId: string; sort: "asc" | "desc" }>;
  filterModel: Record<string, unknown>;
  rowGroupCols: Array<{ id: string; field: string; displayName: string }>;
  groupKeys: string[];
  pivotCols: unknown[];
  pivotMode: boolean;
  valueCols: unknown[];
}

export interface SSRMResponse {
  rows: ReconciliationMatchRow[];
  rowCount: number;
  kpi: KpiAggregates;
}

// ═══════════════════════════════════════════════════════════════════════════
//  OVERRIDE MUTATION PAYLOAD  (FinOps controller cell override)
// ═══════════════════════════════════════════════════════════════════════════

export interface OverridePayload {
  match_id: string;
  new_match_status: MatchStatus;
  review_notes: string;
  reviewed_by: string;
}

// ═══════════════════════════════════════════════════════════════════════════
//  WEBSOCKET EVENTS  (§6 Audit and Feedback)
// ═══════════════════════════════════════════════════════════════════════════

export type WebSocketEventType =
  | "WEBHOOK_ACK"
  | "MATCH_UPDATED"
  | "OPERATION_APPROVED"
  | "OPERATION_EXECUTED"
  | "ANOMALY_RESOLVED"
  | "KPI_REFRESH";

export interface WebSocketEvent {
  event_type: WebSocketEventType;
  row_id: string;
  payload: Partial<ReconciliationMatchRow>;
  timestamp: string;
  kpi?: KpiAggregates;
}
