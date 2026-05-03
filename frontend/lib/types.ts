/**
 * TypeScript mirrors of the FastAPI backend Pydantic schemas.
 * Keep these in sync with backend/app/schemas/*.py — the API client
 * relies on these shapes.
 */

export type SignalDirection = "LONG" | "SHORT" | "NEUTRAL";

export type EventType =
  | "WAR"
  | "CONFLICT"
  | "SANCTION"
  | "ELECTION"
  | "POLICY"
  | "TERRORISM"
  | "NATURAL_DISASTER"
  | "ECONOMIC"
  | "DIPLOMATIC"
  | "OTHER";

export type EventSeverity = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export type AlertOperator = "GT" | "GTE" | "LT" | "LTE" | "EQ";

export interface CorrelatedAsset {
  asset: string;
  correlation: number;            // [-1, 1]
  expected_impact: SignalDirection;
  magnitude?: number | null;
  lag_minutes?: number | null;
}

export interface TradingSignal {
  id: string;
  asset: string;
  direction: SignalDirection;
  confidence: number;             // [0, 1]
  uncertainty: number;            // [0, 1]
  gti: number;                    // [0, 100]
  explanation: string;
  correlated_assets: CorrelatedAsset[];
  event_id?: string | null;
  timestamp: string;              // ISO-8601
}

export interface GeopoliticalEvent {
  id: string;
  title: string;
  summary: string;
  event_type: EventType;
  severity: EventSeverity;
  region?: string | null;
  countries: string[];            // ISO 3166-1 alpha-2
  source?: string | null;
  source_url?: string | null;
  occurred_at: string;
  ingested_at: string;
  raw_data?: Record<string, unknown> | null;
}

export interface AlertRule {
  id: string;
  user_id: string;
  asset: string;
  metric: string;
  operator: AlertOperator;
  threshold: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ListSignalsParams {
  asset?: string;
  event_id?: string;
  since?: string;
  until?: string;
  min_confidence?: number;
  limit?: number;
  offset?: number;
}

export interface ListEventsParams {
  event_type?: EventType;
  severity?: EventSeverity;
  region?: string;
  limit?: number;
  offset?: number;
}

/** The envelope our WebSocket fan-out uses for `signal.created` frames. */
export type WSMessage =
  | { event: "connected"; data: { stream: string } }
  | { event: "signal.created"; data: TradingSignal };
