/**
 * KpiWidgets.tsx – AG Grid Financial Investigation Studio KPI Cards
 * =================================================================
 * Team CrackerX · PayPal AI Hackathon 2026
 *
 * Architecture reference (§4 AG Grid Financial Investigation Studio):
 *   "Integrated Charts and KPI Widgets:
 *     - Total Trapped Working Capital
 *     - Dollars Reconciled
 *     - Dollars Requiring Review"
 *
 * Features:
 *   • Animated number counter on value change (requestAnimationFrame-based,
 *     zero DOM frame drops)
 *   • Subscribes to WS KPI_REFRESH events for real-time updates
 *   • Formats INR/USD currency with Intl.NumberFormat
 *   • Colour-coded: Trapped=amber, Reconciled=emerald, Review=rose
 */
"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import { useWebSocket } from "./websocket_provider";
import type { KpiAggregates, WebSocketEvent } from "./types";

// ═══════════════════════════════════════════════════════════════════════════
//  CURRENCY FORMATTER
// ═══════════════════════════════════════════════════════════════════════════

function formatCurrency(value: string, currency: string): string {
  const num = parseFloat(value);
  if (isNaN(num)) return "—";

  try {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: currency || "INR",
      maximumFractionDigits: 0,
      notation: num >= 1_000_000 ? "compact" : "standard",
      compactDisplay: "short",
    }).format(num);
  } catch {
    // Fallback for unsupported currency codes
    return `${currency} ${num.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;
  }
}

// ═══════════════════════════════════════════════════════════════════════════
//  ANIMATED NUMBER HOOK
// ═══════════════════════════════════════════════════════════════════════════

/**
 * useAnimatedNumber – smoothly interpolates from previous to next numeric
 * value over `durationMs` milliseconds using requestAnimationFrame.
 * Zero setTimeout/setInterval — zero dropped frames.
 */
function useAnimatedNumber(target: number, durationMs = 800): number {
  const [displayed, setDisplayed] = useState(target);
  const rafRef = useRef<number | null>(null);
  const startRef = useRef<number | null>(null);
  const fromRef = useRef(target);

  useEffect(() => {
    const from = fromRef.current;
    const to = target;
    if (from === to) return;

    startRef.current = null;

    const animate = (timestamp: number) => {
      if (startRef.current === null) startRef.current = timestamp;
      const elapsed = timestamp - startRef.current;
      const progress = Math.min(elapsed / durationMs, 1);

      // Ease-out cubic
      const ease = 1 - Math.pow(1 - progress, 3);
      const current = from + (to - from) * ease;

      setDisplayed(current);

      if (progress < 1) {
        rafRef.current = requestAnimationFrame(animate);
      } else {
        fromRef.current = to;
      }
    };

    if (rafRef.current) cancelAnimationFrame(rafRef.current);
    rafRef.current = requestAnimationFrame(animate);

    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, [target, durationMs]);

  return displayed;
}

// ═══════════════════════════════════════════════════════════════════════════
//  INDIVIDUAL KPI CARD
// ═══════════════════════════════════════════════════════════════════════════

interface KpiCardProps {
  label: string;
  value: string;
  currency: string;
  delta?: string | null;        // e.g. "+₹12,00,000 since last refresh"
  colorClass: string;           // Tailwind colour token for accent
  iconSvg: React.ReactNode;
  isLoading?: boolean;
  subtitle?: string;
}

function KpiCard({
  label,
  value,
  currency,
  delta,
  colorClass,
  iconSvg,
  isLoading,
  subtitle,
}: KpiCardProps) {
  const numericValue = parseFloat(value) || 0;
  const animated = useAnimatedNumber(numericValue);

  // Build a synthetic animated string for display
  const displayValue = formatCurrency(animated.toFixed(4), currency);

  return (
    <div
      className={`
        relative flex flex-col gap-3 rounded-xl border bg-slate-900/80
        p-5 shadow-lg backdrop-blur-sm transition-all duration-300
        hover:shadow-xl hover:scale-[1.01]
        border-${colorClass}-500/20
      `}
    >
      {/* Top row: icon + label */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-2">
          <span className={`text-${colorClass}-400`}>{iconSvg}</span>
          <span className="text-sm font-medium text-slate-400">{label}</span>
        </div>
        {isLoading && (
          <span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-600 border-t-slate-300" />
        )}
      </div>

      {/* Main value */}
      {isLoading ? (
        <div className="h-9 w-40 animate-pulse rounded-md bg-slate-700/60" />
      ) : (
        <span
          className={`text-3xl font-bold tracking-tight text-${colorClass}-300`}
        >
          {displayValue}
        </span>
      )}

      {/* Subtitle + delta */}
      <div className="flex items-center justify-between">
        {subtitle && (
          <span className="text-xs text-slate-500">{subtitle}</span>
        )}
        {delta && (
          <span
            className={`text-xs font-medium ${
              delta.startsWith("+")
                ? "text-emerald-400"
                : delta.startsWith("-")
                ? "text-rose-400"
                : "text-slate-400"
            }`}
          >
            {delta}
          </span>
        )}
      </div>

      {/* Colour accent bar */}
      <div
        className={`absolute bottom-0 left-0 h-0.5 w-full rounded-b-xl bg-gradient-to-r from-${colorClass}-500/60 to-transparent`}
      />
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
//  ICONS
// ═══════════════════════════════════════════════════════════════════════════

const LockIcon = (
  <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H6.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z" />
  </svg>
);

const CheckIcon = (
  <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
);

const EyeIcon = (
  <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z" />
    <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
  </svg>
);

// ═══════════════════════════════════════════════════════════════════════════
//  MAIN KPI WIDGETS COMPONENT
// ═══════════════════════════════════════════════════════════════════════════

interface KpiWidgetsProps {
  /** Initial KPI data from the AI investigation response */
  initialKpi: KpiAggregates | null;
  /** Whether the initial data is loading */
  isLoading?: boolean;
}

export function KpiWidgets({ initialKpi, isLoading = false }: KpiWidgetsProps) {
  const [kpi, setKpi] = useState<KpiAggregates | null>(initialKpi);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [flashingField, setFlashingField] = useState<string | null>(null);
  const { subscribe } = useWebSocket();

  // Sync with parent-provided initial KPI
  useEffect(() => {
    if (initialKpi) setKpi(initialKpi);
  }, [initialKpi]);

  // Subscribe to real-time KPI updates from WebSocket
  const handleKpiRefresh = useCallback((event: WebSocketEvent) => {
    if (event.kpi) {
      setKpi(event.kpi);
      setLastUpdated(new Date());

      // Briefly flash the relevant card
      if (event.event_type === "MATCH_UPDATED") {
        setFlashingField("dollars_reconciled");
        setTimeout(() => setFlashingField(null), 1500);
      } else if (event.event_type === "KPI_REFRESH") {
        setFlashingField("all");
        setTimeout(() => setFlashingField(null), 1500);
      }
    }
  }, []);

  useEffect(() => {
    const unsubRefresh = subscribe("KPI_REFRESH", handleKpiRefresh);
    const unsubMatch = subscribe("MATCH_UPDATED", handleKpiRefresh);
    const unsubWebhook = subscribe("WEBHOOK_ACK", handleKpiRefresh);
    return () => {
      unsubRefresh();
      unsubMatch();
      unsubWebhook();
    };
  }, [subscribe, handleKpiRefresh]);

  const currency = kpi?.currency ?? "INR";

  return (
    <div className="space-y-3">
      {/* Header row */}
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold uppercase tracking-widest text-slate-400">
          Financial Summary
        </h2>
        {lastUpdated && (
          <span className="text-xs text-slate-500">
            Updated {lastUpdated.toLocaleTimeString()}
          </span>
        )}
      </div>

      {/* Three KPI cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div
          className={`transition-all duration-300 ${
            flashingField === "all" || flashingField === "total_trapped_working_capital"
              ? "ring-2 ring-amber-400/40 ring-offset-1 ring-offset-slate-950 rounded-xl"
              : ""
          }`}
        >
          <KpiCard
            label="Total Trapped Working Capital"
            value={kpi?.total_trapped_working_capital ?? "0"}
            currency={currency}
            colorClass="amber"
            iconSvg={LockIcon}
            isLoading={isLoading && !kpi}
            subtitle="Unmatched + Pending Review"
          />
        </div>

        <div
          className={`transition-all duration-300 ${
            flashingField === "all" || flashingField === "dollars_reconciled"
              ? "ring-2 ring-emerald-400/40 ring-offset-1 ring-offset-slate-950 rounded-xl"
              : ""
          }`}
        >
          <KpiCard
            label="Dollars Reconciled"
            value={kpi?.dollars_reconciled ?? "0"}
            currency={currency}
            colorClass="emerald"
            iconSvg={CheckIcon}
            isLoading={isLoading && !kpi}
            subtitle="Deterministic + Fuzzy Matched"
          />
        </div>

        <div
          className={`transition-all duration-300 ${
            flashingField === "all" || flashingField === "dollars_requiring_review"
              ? "ring-2 ring-rose-400/40 ring-offset-1 ring-offset-slate-950 rounded-xl"
              : ""
          }`}
        >
          <KpiCard
            label="Dollars Requiring Review"
            value={kpi?.dollars_requiring_review ?? "0"}
            currency={currency}
            colorClass="rose"
            iconSvg={EyeIcon}
            isLoading={isLoading && !kpi}
            subtitle="Fuzzy matches awaiting controller"
          />
        </div>
      </div>
    </div>
  );
}
