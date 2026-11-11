/**
 * FinancialStudioGrid.tsx – AG Grid Enterprise Financial Investigation Studio
 * ===========================================================================
 * Team CrackerX · PayPal AI Hackathon 2026
 *
 * Architecture reference (§4 AG Grid Financial Investigation Studio):
 *   "Drives the AG Grid Enterprise Server-Side Row Model (SSRM)"
 *   "Master-Detail: lazy-loaded evidence"
 *   "Fires a WebSocket event to applyServerSideTransactionAsync via getRowId.
 *    The AG Grid row flashes green in real time without dropping a single DOM frame."
 *
 * Features:
 *   1. SSRM with server-side pagination, sorting, multi-level grouping
 *   2. Custom Cell Renderers: Status, Match Confidence, Variance badges
 *   3. Interactive cell editor for FinOps controller override
 *   4. Master-Detail: lazy-fetches EvidenceDetail on row expand
 *   5. WebSocket → applyServerSideTransactionAsync (zero DOM frame drops)
 *   6. Context menu with Saved Investigations
 *   7. Sidebar with Columns / Filters panels
 *   8. Full AG Grid Enterprise licence key from env
 */
"use client";

import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { AgGridReact } from "ag-grid-react";
import {
  ColDef,
  ColGroupDef,
  GetRowIdParams,
  GridApi,
  GridReadyEvent,
  IServerSideDatasource,
  IServerSideGetRowsParams,
  ICellRendererParams,
  ICellEditorParams,
  IDetailCellRendererParams,
  MenuItemDef,
  GetContextMenuItemsParams,
} from "ag-grid-community";

// AG Grid Enterprise modules
import {
  ModuleRegistry,
  ClientSideRowModelModule,
  ValidationModule,
  RowSelectionModule,
  ColumnAutoSizeModule,
  TextFilterModule,
  NumberFilterModule,
  DateFilterModule,
  CustomFilterModule,
  CellStyleModule,
} from "ag-grid-community";
import {
  ServerSideRowModelModule,
  MasterDetailModule,
  ColumnsToolPanelModule,
  FiltersToolPanelModule,
  RowGroupingModule,
  MenuModule,
  ClipboardModule,
  SetFilterModule,
} from "ag-grid-enterprise";

import "ag-grid-community/styles/ag-grid.css";
import "ag-grid-community/styles/ag-theme-quartz.css";

import { useWebSocket } from "./websocket_provider";
import type {
  EvidenceDetail,
  KpiAggregates,
  MatchStatus,
  OverridePayload,
  ReconciliationMatchRow,
  SSRMRequest,
  SSRMResponse,
  WebSocketEvent,
} from "./types";

// ═══════════════════════════════════════════════════════════════════════════
//  AG GRID ENTERPRISE LICENCE
// ═══════════════════════════════════════════════════════════════════════════

// Licence key comes from .env.local → NEXT_PUBLIC_AG_GRID_LICENSE_KEY
// The LicenseManager import path differs by version:
import { LicenseManager } from "ag-grid-enterprise";
LicenseManager.setLicenseKey(
  process.env.NEXT_PUBLIC_AG_GRID_LICENSE_KEY ?? ""
);

// ═══════════════════════════════════════════════════════════════════════════
//  MODULE REGISTRATION
// ═══════════════════════════════════════════════════════════════════════════

ModuleRegistry.registerModules([
  ClientSideRowModelModule,
  ValidationModule,
  RowSelectionModule,
  ColumnAutoSizeModule,
  TextFilterModule,
  NumberFilterModule,
  DateFilterModule,
  CustomFilterModule,
  SetFilterModule,
  CellStyleModule,
  ServerSideRowModelModule,
  MasterDetailModule,
  ColumnsToolPanelModule,
  FiltersToolPanelModule,
  RowGroupingModule,
  MenuModule,
  ClipboardModule,
]);

// ═══════════════════════════════════════════════════════════════════════════
//  API BASE URL
// ═══════════════════════════════════════════════════════════════════════════

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ═══════════════════════════════════════════════════════════════════════════
//  CUSTOM CELL RENDERERS
// ═══════════════════════════════════════════════════════════════════════════

/** 1. Status Badge Renderer */
function StatusBadgeRenderer(params: ICellRendererParams<ReconciliationMatchRow>) {
  const status = params.value as MatchStatus | undefined;
  if (!status) return null;

  const config: Record<MatchStatus, { label: string; classes: string }> = {
    matched: {
      label: "Matched",
      classes: "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30",
    },
    partial: {
      label: "Partial",
      classes: "bg-blue-500/20 text-blue-300 border border-blue-500/30",
    },
    unmatched: {
      label: "Unmatched",
      classes: "bg-rose-500/20 text-rose-300 border border-rose-500/30",
    },
    disputed: {
      label: "Disputed",
      classes: "bg-orange-500/20 text-orange-300 border border-orange-500/30",
    },
    review_required: {
      label: "Review Required",
      classes: "bg-amber-500/20 text-amber-300 border border-amber-500/30 animate-pulse",
    },
  };

  const { label, classes } = config[status] ?? {
    label: status,
    classes: "bg-slate-500/20 text-slate-300 border border-slate-500/30",
  };

  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${classes}`}
    >
      {label}
    </span>
  );
}

/** 2. Match Confidence Renderer */
function ConfidenceRenderer(params: ICellRendererParams<ReconciliationMatchRow>) {
  const rawScore = params.value as string | null;
  if (rawScore === null || rawScore === undefined) return <span className="text-slate-500 text-xs">—</span>;

  const pct = Math.round(parseFloat(rawScore) * 100);
  const barWidth = `${pct}%`;

  const colorClass =
    pct >= 95 ? "bg-emerald-500" :
    pct >= 70 ? "bg-blue-500" :
    pct >= 40 ? "bg-amber-500" : "bg-rose-500";

  return (
    <div className="flex items-center gap-2 w-full">
      <div className="relative h-1.5 flex-1 rounded-full bg-slate-700 overflow-hidden">
        <div
          className={`absolute left-0 top-0 h-full rounded-full ${colorClass} transition-all duration-500`}
          style={{ width: barWidth }}
        />
      </div>
      <span className={`text-xs font-mono font-semibold w-9 text-right ${
        pct >= 95 ? "text-emerald-400" :
        pct >= 70 ? "text-blue-400" :
        pct >= 40 ? "text-amber-400" : "text-rose-400"
      }`}>
        {pct}%
      </span>
    </div>
  );
}

/** 3. Variance Flag Renderer */
function VarianceFlagRenderer(params: ICellRendererParams<ReconciliationMatchRow>) {
  const amount = params.value as string | null;
  const category = (params.data as ReconciliationMatchRow | undefined)?.variance_category;
  const currency = (params.data as ReconciliationMatchRow | undefined)?.currency ?? "";

  if (!amount || amount === "null") {
    return <span className="text-slate-500 text-xs">—</span>;
  }

  const num = parseFloat(amount);
  const formatted = new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: currency || "INR",
    maximumFractionDigits: 2,
  }).format(Math.abs(num));

  const categoryConfig: Record<string, { label: string; classes: string }> = {
    EXACT:       { label: "✓ Exact",    classes: "text-emerald-400" },
    FEE:         { label: "⟳ Fee",      classes: "text-blue-400" },
    FX_DRIFT:    { label: "⇅ FX Drift", classes: "text-amber-400" },
    SIGNIFICANT: { label: "⚠ Sig.",     classes: "text-rose-400 font-bold" },
  };

  const { label, classes } = category
    ? categoryConfig[category] ?? { label: category, classes: "text-slate-400" }
    : { label: "", classes: "" };

  return (
    <div className="flex items-center gap-2">
      <span className={`text-xs font-mono ${num < 0 ? "text-rose-400" : num > 0 ? "text-amber-400" : "text-slate-400"}`}>
        {num > 0 ? "+" : ""}{formatted}
      </span>
      {label && (
        <span className={`text-xs ${classes}`}>{label}</span>
      )}
    </div>
  );
}

/** 4. Amount Renderer – formats Decimal strings from backend */
function AmountRenderer(params: ICellRendererParams) {
  const value = params.value as string | null;
  const currency = (params.data as ReconciliationMatchRow | undefined)?.currency ?? "INR";
  if (!value) return <span className="text-slate-500 text-xs">—</span>;

  const num = parseFloat(value);
  const formatted = new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency,
    maximumFractionDigits: 2,
  }).format(num);

  return (
    <span className="font-mono text-sm text-slate-200">{formatted}</span>
  );
}

/** 5. Match Method Badge */
function MatchMethodRenderer(params: ICellRendererParams) {
  const method = params.value as string | undefined;
  if (!method) return null;

  const config: Record<string, { label: string; classes: string }> = {
    deterministic_id:   { label: "ID",       classes: "bg-emerald-900/40 text-emerald-300" },
    deterministic_rule: { label: "Rule",      classes: "bg-blue-900/40 text-blue-300" },
    fuzzy_trgm:         { label: "~ Fuzzy",   classes: "bg-purple-900/40 text-purple-300" },
    manual_review:      { label: "✎ Manual",  classes: "bg-slate-700/60 text-slate-300" },
  };

  const { label, classes } = config[method] ?? { label: method, classes: "bg-slate-700/60 text-slate-300" };
  return (
    <span className={`inline-flex items-center rounded px-1.5 py-0.5 text-xs font-medium ${classes}`}>
      {label}
    </span>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
//  CUSTOM CELL EDITOR  (FinOps Controller Override)
// ═══════════════════════════════════════════════════════════════════════════

interface OverrideEditorState {
  status: MatchStatus;
  notes: string;
}

function MatchStatusCellEditor(
  params: ICellEditorParams<ReconciliationMatchRow>
) {
  const [state, setState] = useState<OverrideEditorState>({
    status: params.value as MatchStatus,
    notes: params.data?.review_notes ?? "",
  });
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const statusOptions: MatchStatus[] = [
    "matched",
    "partial",
    "unmatched",
    "disputed",
    "review_required",
  ];

  const handleSave = async () => {
    setIsSaving(true);
    setError(null);
    try {
      const payload: OverridePayload = {
        match_id: params.data!.id,
        new_match_status: state.status,
        review_notes: state.notes,
        reviewed_by: "finops_controller", // Real app: pull from auth session
      };

      const res = await fetch(`${API_BASE}/api/v1/matches/${params.data!.id}/override`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) throw new Error(`Server responded ${res.status}`);
      params.stopEditing();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="z-50 w-72 rounded-lg border border-slate-700 bg-slate-900 p-4 shadow-2xl">
      <h3 className="mb-3 text-sm font-semibold text-slate-200">
        Override Match Status
      </h3>

      {/* Status selector */}
      <label className="mb-1 block text-xs text-slate-400">New Status</label>
      <select
        className="mb-3 w-full rounded-md border border-slate-700 bg-slate-800 px-3 py-1.5 text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/40"
        value={state.status}
        onChange={(e) => setState((s) => ({ ...s, status: e.target.value as MatchStatus }))}
        autoFocus
      >
        {statusOptions.map((opt) => (
          <option key={opt} value={opt}>
            {opt.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
          </option>
        ))}
      </select>

      {/* Review notes */}
      <label className="mb-1 block text-xs text-slate-400">Review Notes</label>
      <textarea
        className="mb-3 w-full rounded-md border border-slate-700 bg-slate-800 px-3 py-1.5 text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/40 resize-none"
        rows={3}
        placeholder="Explain the override reason..."
        value={state.notes}
        onChange={(e) => setState((s) => ({ ...s, notes: e.target.value }))}
      />

      {/* Error */}
      {error && (
        <p className="mb-2 text-xs text-rose-400">⚠ {error}</p>
      )}

      {/* Four-Eyes notice */}
      <p className="mb-3 text-xs text-amber-400/80">
        ⚑ This change requires a second approver (Four-Eyes policy).
      </p>

      {/* Action buttons */}
      <div className="flex gap-2">
        <button
          onClick={handleSave}
          disabled={isSaving}
          className="flex-1 rounded-md bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {isSaving ? "Saving…" : "Stage Override"}
        </button>
        <button
          onClick={() => params.stopEditing(true)}
          className="rounded-md border border-slate-700 px-3 py-1.5 text-sm text-slate-300 hover:bg-slate-800 transition-colors"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
//  MASTER-DETAIL: EVIDENCE PANEL (Lazy-loaded on row expand)
// ═══════════════════════════════════════════════════════════════════════════

function EvidenceDetailPanel(params: IDetailCellRendererParams<ReconciliationMatchRow>) {
  const matchId = params.data?.id;
  const [evidence, setEvidence] = useState<EvidenceDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"invoice" | "webhook" | "journal" | "anomalies">("invoice");

  useEffect(() => {
    if (!matchId) return;
    let cancelled = false;

    async function fetchEvidence() {
      try {
        const res = await fetch(`${API_BASE}/api/v1/evidence/${matchId}`);
        if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
        const data: EvidenceDetail = await res.json();
        if (!cancelled) setEvidence(data);
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : "Failed to load evidence");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    fetchEvidence();
    return () => { cancelled = true; };
  }, [matchId]);

  if (loading) {
    return (
      <div className="flex items-center gap-3 p-6 text-slate-400">
        <span className="h-5 w-5 animate-spin rounded-full border-2 border-slate-600 border-t-blue-400" />
        <span className="text-sm">Loading evidence…</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 text-sm text-rose-400">⚠ Failed to load evidence: {error}</div>
    );
  }

  if (!evidence) return null;

  const tabs = [
    { id: "invoice" as const, label: "ERP Invoice" },
    { id: "webhook" as const, label: "PayPal Webhook" },
    { id: "journal" as const, label: `Journal Lines (${evidence.journal_lines.length})` },
    { id: "anomalies" as const, label: `Anomalies (${evidence.anomaly_flags.length})` },
  ];

  return (
    <div className="border-t border-slate-800 bg-slate-950/60 p-4">
      {/* Tab bar */}
      <div className="mb-4 flex gap-1 border-b border-slate-800 pb-2">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`rounded-t px-3 py-1.5 text-xs font-medium transition-colors ${
              activeTab === tab.id
                ? "bg-blue-600/20 text-blue-300 border-b-2 border-blue-500"
                : "text-slate-500 hover:text-slate-300"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {activeTab === "invoice" && evidence.erp_invoice && (
        <div className="grid grid-cols-2 gap-x-8 gap-y-2 text-sm">
          <EvidenceRow label="Invoice ID" value={evidence.erp_invoice.internal_invoice_id} />
          <EvidenceRow label="Vendor" value={evidence.erp_invoice.vendor_name} />
          <EvidenceRow label="Email" value={evidence.erp_invoice.vendor_email ?? "⚠ Missing"} warn={!evidence.erp_invoice.vendor_email} />
          <EvidenceRow label="Amount" value={`${evidence.erp_invoice.currency} ${evidence.erp_invoice.erp_amount}`} />
          <EvidenceRow label="ERP Status" value={evidence.erp_invoice.erp_status_normalised ?? evidence.erp_invoice.erp_status} />
        </div>
      )}

      {activeTab === "webhook" && (
        <pre className="max-h-64 overflow-auto rounded-md bg-slate-900 p-3 text-xs text-green-300 font-mono leading-relaxed">
          {evidence.raw_paypal_webhook_json
            ? JSON.stringify(JSON.parse(evidence.raw_paypal_webhook_json), null, 2)
            : "No webhook payload available"}
        </pre>
      )}

      {activeTab === "journal" && (
        <div className="overflow-auto">
          <table className="w-full text-xs text-slate-300">
            <thead>
              <tr className="border-b border-slate-800 text-slate-500">
                <th className="pb-2 text-left font-medium">Type</th>
                <th className="pb-2 text-left font-medium">Account</th>
                <th className="pb-2 text-right font-medium">Amount</th>
                <th className="pb-2 text-left font-medium">Memo</th>
              </tr>
            </thead>
            <tbody>
              {evidence.journal_lines.map((line) => (
                <tr key={line.id} className="border-b border-slate-800/50">
                  <td className="py-1.5 pr-4">
                    <span className={`font-mono font-semibold ${
                      line.entry_type === "debit" ? "text-rose-400" : "text-emerald-400"
                    }`}>
                      {line.entry_type.toUpperCase()}
                    </span>
                  </td>
                  <td className="py-1.5 pr-4 font-mono text-blue-300">{line.account_code}</td>
                  <td className="py-1.5 pr-4 text-right font-mono">
                    {line.currency} {line.amount}
                  </td>
                  <td className="py-1.5 text-slate-500">{line.memo ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {activeTab === "anomalies" && (
        <div className="space-y-2">
          {evidence.anomaly_flags.length === 0 ? (
            <p className="text-xs text-slate-500">No anomaly flags for this match.</p>
          ) : (
            evidence.anomaly_flags.map((flag) => (
              <div
                key={flag.id}
                className={`rounded-md border p-3 text-xs ${
                  flag.severity === "critical"
                    ? "border-rose-500/30 bg-rose-900/20 text-rose-300"
                    : flag.severity === "warning"
                    ? "border-amber-500/30 bg-amber-900/20 text-amber-300"
                    : "border-blue-500/30 bg-blue-900/20 text-blue-300"
                }`}
              >
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <span className="font-mono font-semibold">{flag.rule_code}</span>
                    <p className="mt-1 text-slate-300">{flag.description}</p>
                    {flag.suggested_action && (
                      <p className="mt-1 text-slate-400">→ {flag.suggested_action}</p>
                    )}
                  </div>
                  <span className="shrink-0 uppercase text-xs opacity-70">{flag.severity}</span>
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}

function EvidenceRow({ label, value, warn }: { label: string; value: string; warn?: boolean }) {
  return (
    <>
      <span className="text-slate-500">{label}</span>
      <span className={warn ? "text-rose-400 font-medium" : "text-slate-200"}>{value}</span>
    </>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
//  SSRM DATASOURCE
// ═══════════════════════════════════════════════════════════════════════════

function buildSSRMDatasource(
  onKpiUpdate: (kpi: KpiAggregates) => void
): IServerSideDatasource {
  return {
    getRows: async (params: IServerSideGetRowsParams) => {
      const { request } = params;

      const body: SSRMRequest = {
        startRow: request.startRow ?? 0,
        endRow: request.endRow ?? 100,
        sortModel: request.sortModel.map((s) => ({
          colId: s.colId,
          sort: s.sort as "asc" | "desc",
        })),
        filterModel: request.filterModel as Record<string, unknown>,
        rowGroupCols: request.rowGroupCols.map((c) => ({
          id: c.id,
          field: c.field ?? "",
          displayName: c.displayName,
        })),
        groupKeys: request.groupKeys as string[],
        pivotCols: [],
        pivotMode: false,
        valueCols: [],
      };

      try {
        const res = await fetch(`${API_BASE}/api/v1/grid/rows`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });

        if (!res.ok) {
          params.fail();
          return;
        }

        const data: SSRMResponse = await res.json();
        params.success({
          rowData: data.rows,
          rowCount: data.rowCount,
        });

        // Update KPI sidebar
        onKpiUpdate(data.kpi);
      } catch {
        params.fail();
      }
    },
  };
}

// ═══════════════════════════════════════════════════════════════════════════
//  COLUMN DEFINITIONS
// ═══════════════════════════════════════════════════════════════════════════

export const COLUMN_DEFS: ColDef[] = [
  {
    headerName: "TRANSACTION ID",
    field: "transaction_id",
    filter: "agTextColumnFilter",
    floatingFilter: true,
    width: 220,
    cellClass: "font-mono text-xs text-slate-200 select-all",
    pinned: "left",
    enableRowGroup: true,
  },
  {
    headerName: "TIMESTAMP",
    field: "timestamp",
    filter: "agDateColumnFilter",
    floatingFilter: true,
    filterParams: {
      browserDatePicker: true,
    },
    width: 190,
    cellClass: "font-mono text-xs text-slate-400",
    valueFormatter: (p: any) =>
      p.value ? new Date(p.value).toLocaleString("en-IN") : "—",
  },
  {
    headerName: "VENDOR EMAIL",
    field: "vendor_email",
    filter: "agTextColumnFilter",
    floatingFilter: true,
    width: 230,
    cellClass: "font-mono text-xs text-slate-300",
    enableRowGroup: true,
  },
  {
    headerName: "AMOUNT",
    field: "amount",
    filter: "agNumberColumnFilter",
    floatingFilter: true,
    width: 155,
    type: "numericColumn",
    cellRenderer: AmountRenderer,
    aggFunc: "sum",
  },
  {
    headerName: "CUR",
    field: "currency",
    filter: false,
    floatingFilter: false,
    width: 85,
    minWidth: 80,
    maxWidth: 110,
    cellClass: "font-mono text-xs text-slate-400 text-center uppercase font-medium",
    enableRowGroup: true,
  },
  {
    headerName: "ERP STATUS",
    field: "erp_status",
    filter: "agSetColumnFilter",
    filterParams: {
      values: [
        "SETTLED",
        "PENDING",
        "PENDING_APPROVAL",
        "FAILED",
        "RECONCILED",
        "EXECUTED",
        "UNMATCHED",
        "DISPUTED",
      ],
      defaultToNothingSelected: false,
    },
    floatingFilter: true,
    width: 195,
    minWidth: 180,
    cellRenderer: StatusBadgeRenderer,
    enableRowGroup: true,
  },
  {
    headerName: "FAILURE REASON / ROOT CAUSE",
    field: "failure_reason",
    filter: "agSetColumnFilter",
    filterParams: {
      values: [
        "FX Variance Limit Breached: Δ₹50",
        "FX Variance Limit Breached: Δ₹50.00",
        "FX Variance Limit Breached: Δ₹100",
        "FX Variance Limit Breached: Δ₹100.00",
        "PayPal API Error: INVALID_RECEIVER_ACCOUNT",
        "PayPal Sandbox API execution error: INVALID_RECEIVER_ACCOUNT.",
        "Missing clearance status on ERP ledger.",
        "Four-Eyes approval required for FX variance",
        "Gateway Timeout: 504",
      ],
      defaultToNothingSelected: false,
    },
    floatingFilter: true,
    width: 360,
    minWidth: 280,
  },
  {
    headerName: "NOTES",
    field: "notes",
    filter: false,
    floatingFilter: false,
    flex: 1,
    minWidth: 200,
    cellClass: "font-mono text-xs text-slate-400 truncate",
  },
];

// ═══════════════════════════════════════════════════════════════════════════
//  MAIN COMPONENT
// ═══════════════════════════════════════════════════════════════════════════

interface FinancialStudioGridProps {
  /** Initial AI investigation response – pre-populates filters if provided */
  initialQuery?: string;
  onKpiUpdate?: (kpi: KpiAggregates) => void;
}

export function FinancialStudioGrid({
  initialQuery,
  onKpiUpdate,
}: FinancialStudioGridProps) {
  const gridApiRef = useRef<GridApi<ReconciliationMatchRow> | null>(null);
  const { subscribe } = useWebSocket();

  // ── WebSocket → applyServerSideTransactionAsync ──────────────────
  const handleWebhookAck = useCallback(
    async (event: WebSocketEvent) => {
      const api = gridApiRef.current;
      if (!api) return;

      // Update the specific row in the SSRM store without full refresh
      // The architecture mandates: "without dropping a single DOM frame"
      const rowNode = api.getRowNode(event.row_id);
      if (!rowNode) return;

      // Merge the incoming payload onto the current row data
      const updatedData: ReconciliationMatchRow = {
        ...(rowNode.data as ReconciliationMatchRow),
        ...event.payload,
      };

      // applyServerSideTransactionAsync is non-blocking and frame-safe
      await api.applyServerSideTransactionAsync({
        update: [updatedData],
      });

      // Flash the updated row green (AG Grid native flash)
      api.flashCells({
        rowNodes: [rowNode],
        
      });
    },
    []
  );

  // Subscribe to all real-time events that require row updates
  useEffect(() => {
    const unsubWebhook = subscribe("WEBHOOK_ACK", handleWebhookAck);
    const unsubMatch = subscribe("MATCH_UPDATED", handleWebhookAck);
    const unsubExecuted = subscribe("OPERATION_EXECUTED", handleWebhookAck);
    return () => {
      unsubWebhook();
      unsubMatch();
      unsubExecuted();
    };
  }, [subscribe, handleWebhookAck]);

  // ── Grid ready ───────────────────────────────────────────────────
  const handleGridReady = useCallback(
    (event: GridReadyEvent<ReconciliationMatchRow>) => {
      gridApiRef.current = event.api;

      const datasource = buildSSRMDatasource((kpi) => {
        onKpiUpdate?.(kpi);
      });
      event.api.setGridOption("serverSideDatasource", datasource);
    },
    [onKpiUpdate]
  );

  // ── Row ID – must be stable across updates ───────────────────────
  const getRowId = useCallback(
    (params: GetRowIdParams<ReconciliationMatchRow>) => params.data.id,
    []
  );

  // ── Context menu ─────────────────────────────────────────────────
  const getContextMenuItems = useCallback(
    (params: GetContextMenuItemsParams<ReconciliationMatchRow>): any => {
      const matchId = params.node?.data?.id;
      return [
        {
          name: "🔍 Open Evidence Panel",
          action: () => {
            if (params.node) params.node.setExpanded(true);
          },
          disabled: !matchId,
        },
        {
          name: "✎ Override Status",
          action: () => {
            if (params.node) {
              params.api.startEditingCell({
                rowIndex: params.node.rowIndex!,
                colKey: "match_status",
              });
            }
          },
          disabled: !matchId,
        },
        "separator",
        {
          name: "📋 Copy Row",
          action: () => params.api.copySelectedRowsToClipboard(),
        },
        "separator",
        {
          name: "💾 Save Investigation",
          action: () => {
            const filterModel = params.api.getFilterModel();
            const columnState = params.api.getColumnState();
            const saved = {
              name: `Investigation ${new Date().toLocaleTimeString()}`,
              filterModel,
              columnState,
              savedAt: new Date().toISOString(),
            };
            const existing = JSON.parse(
              localStorage.getItem("saved_investigations") ?? "[]"
            ) as unknown[];
            localStorage.setItem(
              "saved_investigations",
              JSON.stringify([...existing, saved])
            );
          },
        },
      ];
    },
    []
  );

  // ── Detail cell renderer params ──────────────────────────────────
  const detailCellRendererParams = useMemo(
    () => ({
      detailGridOptions: {},
    }),
    []
  );

  return (
    <div
      className="ag-theme-quartz-dark h-full w-full"
      style={{
        // Inject CSS variables for the dark financial theme
        // @ts-ignore
        "--ag-background-color": "#0f172a",
        "--ag-foreground-color": "#e2e8f0",
        "--ag-border-color": "#1e293b",
        "--ag-header-background-color": "#0f172a",
        "--ag-header-foreground-color": "#94a3b8",
        "--ag-odd-row-background-color": "#0f172a",
        "--ag-row-hover-color": "#1e293b",
        "--ag-selected-row-background-color": "#1d4ed8/20",
        "--ag-cell-horizontal-border": "solid #1e293b",
        "--ag-row-border-color": "#1e293b",
        "--ag-modal-overlay-background-color": "rgba(0,0,0,0.6)",
        "--ag-popup-shadow": "0 25px 50px -12px rgba(0,0,0,0.5)",
        "--ag-font-size": "13px",
        "--ag-font-family": "Inter, ui-sans-serif, system-ui, sans-serif",
        "--ag-cell-widget-spacing": "12px",
      } as React.CSSProperties}
    >
      <AgGridReact<ReconciliationMatchRow>
        // ── Core ────────────────────────────────────────────────
        rowModelType="serverSide"
        serverSideInitialRowCount={100}
        getRowId={getRowId}
        onGridReady={handleGridReady}

        // ── Column definitions ──────────────────────────────────
        columnDefs={COLUMN_DEFS}
        defaultColDef={{
          sortable: true,
          filter: false, // Strict type-aware filtering: prevent generic text filters from bleeding into every column
          floatingFilter: false,
          resizable: true,
          suppressMovable: false,
          flex: 0,
          minWidth: 80,
        }}

        // ── SSRM settings ───────────────────────────────────────
        cacheBlockSize={100}
        maxBlocksInCache={10}
        rowBuffer={20}
        animateRows={true}

        // ── Multi-level grouping (clusters anomalies natively) ──
        rowGroupPanelShow="always"
        groupDisplayType="multipleColumns"
        suppressAggFuncInHeader={false}

        // ── Master-Detail: lazy evidence panel ──────────────────
        masterDetail={true}
        detailCellRenderer={EvidenceDetailPanel}
        detailRowHeight={420}
        isRowMaster={(data: ReconciliationMatchRow) =>
          // Only matched/review_required rows have detail evidence
          data.match_status === "matched" ||
          data.match_status === "review_required" ||
          data.match_status === "disputed"
        }

        // ── Editing ─────────────────────────────────────────────
        editType="fullRow"
        stopEditingWhenCellsLoseFocus={false}

        // ── Selection ───────────────────────────────────────────
        rowSelection={{ mode: "multiRow" }}
        suppressRowClickSelection={true}

        // ── UI chrome ───────────────────────────────────────────
        sideBar={{
          toolPanels: [
            {
              id: "columns",
              labelDefault: "Columns",
              labelKey: "columns",
              iconKey: "columns",
              toolPanel: "agColumnsToolPanel",
            },
            {
              id: "filters",
              labelDefault: "Filters",
              labelKey: "filters",
              iconKey: "filter",
              toolPanel: "agFiltersToolPanel",
            },
          ],
          defaultToolPanel: "",
          hiddenByDefault: false,
        }}
        statusBar={{
          statusPanels: [
            { statusPanel: "agTotalAndFilteredRowCountComponent", align: "left" },
            { statusPanel: "agSelectedRowCountComponent", align: "center" },
            { statusPanel: "agAggregationComponent", align: "right" },
          ],
        }}

        // ── Context menu ────────────────────────────────────────
        getContextMenuItems={getContextMenuItems}

        // ── Pagination ──────────────────────────────────────────
        pagination={true}
        paginationPageSize={100}
        paginationPageSizeSelector={[50, 100, 250, 500]}

        // ── Loading overlay ─────────────────────────────────────
        loadingOverlayComponent={() => (
          <div className="flex items-center gap-3 text-slate-400 text-sm">
            <span className="h-5 w-5 animate-spin rounded-full border-2 border-slate-600 border-t-blue-400" />
            Fetching reconciliation data…
          </div>
        )}
        noRowsOverlayComponent={() => (
          <div className="text-center text-slate-500">
            <p className="text-lg mb-1">No records found</p>
            <p className="text-sm">Run an AI investigation or adjust your filters</p>
          </div>
        )}
      />
    </div>
  );
}
