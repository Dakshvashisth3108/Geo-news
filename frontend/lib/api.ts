/**
 * Typed client for the GeoIntel Trade FastAPI backend.
 *
 * Usage:
 *   import { api, subscribeToSignals } from "@/lib/api";
 *   const signals = await api.signals.list({ limit: 20 });
 *   const unsubscribe = subscribeToSignals((signal) => {...});
 */

import type {
  AlertRule,
  GeopoliticalEvent,
  ListEventsParams,
  ListSignalsParams,
  TradingSignal,
  WSMessage,
} from "./types";

const RAW_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "http://localhost:8000";
const API_PREFIX = "/api/v1";
const BASE_URL = `${RAW_BASE}${API_PREFIX}`;

// ---------------------------------------------------------------------------
// Errors
// ---------------------------------------------------------------------------

export class APIError extends Error {
  constructor(
    public status: number,
    message: string,
    public payload?: unknown,
  ) {
    super(message);
    this.name = "APIError";
  }
}

// ---------------------------------------------------------------------------
// Internals
// ---------------------------------------------------------------------------

function buildQuery(params?: Record<string, unknown>): string {
  if (!params) return "";
  const usp = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === "") continue;
    usp.set(key, String(value));
  }
  const qs = usp.toString();
  return qs ? `?${qs}` : "";
}

async function request<T>(
  path: string,
  init?: RequestInit & { query?: Record<string, unknown> },
): Promise<T> {
  const { query, headers, ...rest } = init ?? {};
  const url = `${BASE_URL}${path}${buildQuery(query)}`;

  let response: Response;
  try {
    response = await fetch(url, {
      ...rest,
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
        ...headers,
      },
      // Real-time data — never cache by default.
      cache: rest.cache ?? "no-store",
    });
  } catch (cause) {
    throw new APIError(0, `Network error reaching ${url}`, cause);
  }

  if (!response.ok) {
    let payload: unknown;
    try {
      payload = await response.json();
    } catch {
      payload = await response.text().catch(() => null);
    }
    const detail =
      (typeof payload === "object" && payload && "detail" in payload
        ? (payload as { detail: unknown }).detail
        : null) ?? response.statusText;
    throw new APIError(response.status, String(detail), payload);
  }

  // Allow callers to fire-and-forget DELETE / 204s without parsing.
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

// ---------------------------------------------------------------------------
// REST surface
// ---------------------------------------------------------------------------

export const api = {
  // /health is mounted at the app root, not under the v1 prefix.
  health: async () => {
    const res = await fetch(`${RAW_BASE}/health`, { cache: "no-store" });
    if (!res.ok) throw new APIError(res.status, res.statusText);
    return (await res.json()) as {
      status: string;
      service: string;
      environment: string;
    };
  },

  signals: {
    list: (params?: ListSignalsParams) =>
      request<TradingSignal[]>("/signals", { query: params }),
    get: (id: string) => request<TradingSignal>(`/signals/${id}`),
    create: (
      payload: Omit<TradingSignal, "id" | "timestamp"> & { timestamp?: string },
    ) =>
      request<TradingSignal>("/signals", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
  },

  events: {
    list: (params?: ListEventsParams) =>
      request<GeopoliticalEvent[]>("/events", { query: params }),
    get: (id: string) => request<GeopoliticalEvent>(`/events/${id}`),
    create: (payload: Omit<GeopoliticalEvent, "id" | "ingested_at">) =>
      request<GeopoliticalEvent>("/events", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
  },

  alerts: {
    list: (userId: string) =>
      request<AlertRule[]>("/alerts", { query: { user_id: userId } }),
    create: (
      userId: string,
      payload: Omit<AlertRule, "id" | "user_id" | "created_at" | "updated_at">,
    ) =>
      request<AlertRule>("/alerts", {
        method: "POST",
        body: JSON.stringify(payload),
        query: { user_id: userId },
      }),
    delete: (id: string) =>
      request<void>(`/alerts/${id}`, { method: "DELETE" }),
  },
};

// ---------------------------------------------------------------------------
// WebSocket — real-time signal stream
// ---------------------------------------------------------------------------

function wsUrl(): string {
  // Honour an explicit override if the deployment terminates WS on a
  // different host (e.g. behind a different proxy).
  const explicit = process.env.NEXT_PUBLIC_WS_URL?.replace(/\/$/, "");
  if (explicit) return `${explicit}${API_PREFIX}/ws/signals`;

  // Otherwise derive from the API URL — http→ws, https→wss.
  return `${BASE_URL.replace(/^http/, "ws")}/ws/signals`;
}

export interface SignalSubscription {
  /** Close the underlying socket. Idempotent. */
  close: () => void;
  /** Live ref to the underlying WebSocket — useful for status checks. */
  socket: WebSocket;
}

/**
 * Subscribe to the real-time `signal.created` stream.
 *
 * Returns a `SignalSubscription` whose `close()` shuts the socket. Reconnection
 * is intentionally NOT built in here — components should layer their own retry
 * logic (typically inside a useEffect cleanup) so unmount + reconnect cycles
 * stay deterministic.
 */
export function subscribeToSignals(
  onSignal: (signal: TradingSignal) => void,
  onError?: (event: Event) => void,
): SignalSubscription {
  const socket = new WebSocket(wsUrl());

  socket.onmessage = (event) => {
    try {
      const message = JSON.parse(event.data) as WSMessage;
      if (message.event === "signal.created") {
        onSignal(message.data);
      }
    } catch {
      // Malformed frame — ignore. Surfaces as a partial UI state, never a crash.
    }
  };

  if (onError) socket.onerror = onError;

  return {
    socket,
    close: () => {
      if (
        socket.readyState === WebSocket.OPEN ||
        socket.readyState === WebSocket.CONNECTING
      ) {
        socket.close();
      }
    },
  };
}
