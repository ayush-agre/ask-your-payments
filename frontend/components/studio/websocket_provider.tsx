/**
 * websocket_provider.tsx – WebSocket Context Provider
 * =====================================================
 * Team CrackerX · PayPal AI Hackathon 2026
 *
 * Architecture reference (§6 Audit and Feedback):
 *   "Fires a WebSocket event to applyServerSideTransactionAsync via getRowId.
 *    The AG Grid row flashes green in real time without dropping a single DOM frame."
 *
 * Features:
 *   • Auto-reconnect with exponential backoff (max 30s, 10 retries)
 *   • Message routing via event callbacks keyed by WebSocketEventType
 *   • Connection state exposed to consumers via context
 *   • Ref-stable callback registration — zero useEffect re-runs on grid re-renders
 *   • Explicit cleanup on unmount — no leaked WebSocket connections
 */
"use client";

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";
import type { WebSocketEvent, WebSocketEventType } from "./types";

// ═══════════════════════════════════════════════════════════════════════════
//  CONSTANTS
// ═══════════════════════════════════════════════════════════════════════════

const WS_BASE_URL =
  process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000/ws/events";

const INITIAL_RECONNECT_DELAY_MS = 500;
const MAX_RECONNECT_DELAY_MS = 30_000;
const MAX_RECONNECT_ATTEMPTS = 10;

// ═══════════════════════════════════════════════════════════════════════════
//  TYPES
// ═══════════════════════════════════════════════════════════════════════════

export type WSConnectionState = "connecting" | "open" | "closed" | "error";

/** Subscriber callback type */
export type WSEventHandler = (event: WebSocketEvent) => void;

export interface WebSocketContextValue {
  /** Current connection state */
  connectionState: WSConnectionState;
  /** Subscribe to a specific event type. Returns an unsubscribe function. */
  subscribe: (eventType: WebSocketEventType, handler: WSEventHandler) => () => void;
  /** Subscribe to ALL event types. Returns an unsubscribe function. */
  subscribeAll: (handler: WSEventHandler) => () => void;
  /** Number of reconnect attempts made since last successful connection */
  reconnectCount: number;
}

// ═══════════════════════════════════════════════════════════════════════════
//  CONTEXT
// ═══════════════════════════════════════════════════════════════════════════

const WebSocketContext = createContext<WebSocketContextValue | null>(null);

// ═══════════════════════════════════════════════════════════════════════════
//  PROVIDER
// ═══════════════════════════════════════════════════════════════════════════

export function WebSocketProvider({
  children,
  tenantId,
}: {
  children: React.ReactNode;
  tenantId?: string;
}) {
  const [connectionState, setConnectionState] =
    useState<WSConnectionState>("connecting");
  const [reconnectCount, setReconnectCount] = useState(0);

  // Ref-stable maps: eventType → Set<handler>
  const handlersRef = useRef<Map<WebSocketEventType, Set<WSEventHandler>>>(
    new Map()
  );
  const globalHandlersRef = useRef<Set<WSEventHandler>>(new Set());

  // Active WebSocket instance
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectDelayRef = useRef(INITIAL_RECONNECT_DELAY_MS);
  const reconnectAttemptRef = useRef(0);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isMountedRef = useRef(true);

  /**
   * Dispatch a received WebSocketEvent to all registered handlers.
   * Split into typed + global handlers for efficiency.
   */
  const dispatch = useCallback((event: WebSocketEvent) => {
    // Notify type-specific subscribers
    const typed = handlersRef.current.get(event.event_type);
    if (typed) {
      typed.forEach((h) => h(event));
    }
    // Notify wildcard subscribers
    globalHandlersRef.current.forEach((h) => h(event));
  }, []);

  /**
   * Establish (or re-establish) the WebSocket connection.
   */
  const connect = useCallback(() => {
    if (!isMountedRef.current) return;

    const url = tenantId
      ? `${WS_BASE_URL}?tenant_id=${encodeURIComponent(tenantId)}`
      : WS_BASE_URL;

    const ws = new WebSocket(url);
    wsRef.current = ws;
    setConnectionState("connecting");

    ws.onopen = () => {
      if (!isMountedRef.current) return;
      setConnectionState("open");
      reconnectDelayRef.current = INITIAL_RECONNECT_DELAY_MS;
      reconnectAttemptRef.current = 0;
      setReconnectCount(0);
    };

    ws.onmessage = (msgEvent: MessageEvent) => {
      if (!isMountedRef.current) return;
      try {
        const parsed: WebSocketEvent = JSON.parse(msgEvent.data as string);
        dispatch(parsed);
      } catch {
        console.warn("[WS] Received non-JSON message, ignoring:", msgEvent.data);
      }
    };

    ws.onerror = () => {
      if (!isMountedRef.current) return;
      setConnectionState("error");
    };

    ws.onclose = () => {
      if (!isMountedRef.current) return;
      setConnectionState("closed");
      wsRef.current = null;

      // Exponential back-off reconnect
      if (reconnectAttemptRef.current < MAX_RECONNECT_ATTEMPTS) {
        const delay = Math.min(
          reconnectDelayRef.current,
          MAX_RECONNECT_DELAY_MS
        );
        reconnectDelayRef.current = delay * 2;
        reconnectAttemptRef.current += 1;
        setReconnectCount(reconnectAttemptRef.current);

        reconnectTimerRef.current = setTimeout(() => {
          if (isMountedRef.current) connect();
        }, delay);
      } else {
        console.error(
          `[WS] Max reconnect attempts (${MAX_RECONNECT_ATTEMPTS}) reached.`
        );
      }
    };
  }, [dispatch, tenantId]);

  // Initial connection
  useEffect(() => {
    isMountedRef.current = true;
    connect();

    return () => {
      isMountedRef.current = false;
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
      wsRef.current?.close(1000, "Component unmounted");
    };
  }, [connect]);

  /**
   * Subscribe to a specific event type.
   * Returns a stable unsubscribe callback — safe to use in AG Grid callbacks.
   */
  const subscribe = useCallback(
    (eventType: WebSocketEventType, handler: WSEventHandler): (() => void) => {
      if (!handlersRef.current.has(eventType)) {
        handlersRef.current.set(eventType, new Set());
      }
      handlersRef.current.get(eventType)!.add(handler);

      return () => {
        handlersRef.current.get(eventType)?.delete(handler);
      };
    },
    []
  );

  /**
   * Subscribe to ALL event types.
   */
  const subscribeAll = useCallback(
    (handler: WSEventHandler): (() => void) => {
      globalHandlersRef.current.add(handler);
      return () => {
        globalHandlersRef.current.delete(handler);
      };
    },
    []
  );

  const contextValue: WebSocketContextValue = {
    connectionState,
    subscribe,
    subscribeAll,
    reconnectCount,
  };

  return (
    <WebSocketContext.Provider value={contextValue}>
      {children}
    </WebSocketContext.Provider>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
//  HOOK
// ═══════════════════════════════════════════════════════════════════════════

/**
 * useWebSocket – consume the WebSocket context.
 * Must be used inside <WebSocketProvider>.
 */
export function useWebSocket(): WebSocketContextValue {
  const ctx = useContext(WebSocketContext);
  if (!ctx) {
    throw new Error("useWebSocket must be used within a <WebSocketProvider>");
  }
  return ctx;
}

// ═══════════════════════════════════════════════════════════════════════════
//  CONNECTION STATUS BADGE  (small utility component)
// ═══════════════════════════════════════════════════════════════════════════

export function WSConnectionBadge() {
  const { connectionState, reconnectCount } = useWebSocket();

  const styles: Record<WSConnectionState, string> = {
    open: "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30",
    connecting: "bg-amber-500/20 text-amber-400 border border-amber-500/30 animate-pulse",
    closed: "bg-slate-500/20 text-slate-400 border border-slate-500/30",
    error: "bg-red-500/20 text-red-400 border border-red-500/30",
  };

  const labels: Record<WSConnectionState, string> = {
    open: "● Live",
    connecting: reconnectCount > 0
      ? `↻ Reconnecting (${reconnectCount})`
      : "◌ Connecting",
    closed: "○ Disconnected",
    error: "✕ Error",
  };

  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium ${styles[connectionState]}`}
      title={`WebSocket: ${connectionState}`}
    >
      {labels[connectionState]}
    </span>
  );
}
