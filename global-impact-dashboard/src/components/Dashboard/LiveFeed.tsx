import React, { useEffect, useState } from 'react';
import { Radio } from 'lucide-react';

import { Card } from '../UI/primitives/Card';
import { SignalCard } from './SignalCard';
import { api, subscribeToSignals } from '../../lib/api';
import type { TradingSignal } from '../../lib/types';

const MAX_SIGNALS = 25;

type Status = 'connecting' | 'live' | 'error' | 'offline';

/**
 * Real-time signal stream.
 *
 * Hydration plan:
 *   1. On mount, REST-fetch the most recent N signals so the panel is
 *      not empty during the WS handshake.
 *   2. Open the WS subscription; new frames are prepended.
 *   3. On unmount, the subscription's close() runs in the cleanup.
 *
 * Errors are surfaced as a non-blocking footer message; the panel still
 * shows whatever data it has.
 */
export const LiveFeed: React.FC = () => {
  const [signals, setSignals] = useState<TradingSignal[]>([]);
  const [status, setStatus] = useState<Status>('connecting');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    api.signals
      .list({ limit: MAX_SIGNALS })
      .then((initial) => { if (!cancelled) setSignals(initial); })
      .catch((err: Error) => {
        if (cancelled) return;
        setErrorMsg(err.message);
        setStatus('offline');
      });

    const subscription = subscribeToSignals(
      (signal) => {
        setSignals((prev) => {
          const without = prev.filter((s) => s.id !== signal.id);
          return [signal, ...without].slice(0, MAX_SIGNALS);
        });
        setStatus('live');
      },
      () => setStatus('error'),
    );

    subscription.socket.addEventListener('open', () => setStatus('live'));

    return () => {
      cancelled = true;
      subscription.close();
    };
  }, []);

  return (
    <Card className="flex h-full min-h-[400px] flex-col overflow-hidden">
      <div className="flex items-center justify-between border-b border-border/60 px-5 py-3">
        <div className="flex items-center gap-2">
          <Radio className="h-4 w-4 text-primary" />
          <h2 className="text-sm font-semibold">Live Signal Feed</h2>
        </div>
        <StatusPill status={status} />
      </div>

      <div className="flex-1 space-y-3 overflow-y-auto p-4">
        {signals.length === 0
          ? <EmptyState message={errorMsg} />
          : signals.map((s) => <SignalCard key={s.id} signal={s} />)
        }
      </div>
    </Card>
  );
};

const StatusPill: React.FC<{ status: Status }> = ({ status }) => {
  const map = {
    connecting: { label: 'Connecting',  color: 'bg-amber-400' },
    live:       { label: 'Live',        color: 'bg-emerald-400 animate-pulse' },
    error:      { label: 'Reconnecting', color: 'bg-amber-400' },
    offline:    { label: 'Offline',     color: 'bg-rose-400' },
  } as const;
  const { label, color } = map[status];
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-border bg-card px-2 py-0.5 text-[10px] font-mono uppercase tracking-widest text-muted-foreground">
      <span className={`h-1.5 w-1.5 rounded-full ${color}`} />
      {label}
    </span>
  );
};

const EmptyState: React.FC<{ message: string | null }> = ({ message }) => (
  <div className="grid h-full place-items-center text-center">
    <div className="space-y-1">
      <p className="text-sm text-muted-foreground">
        {message ? "Couldn't reach the backend." : 'Waiting for the first signal…'}
      </p>
      {message && <p className="text-[11px] font-mono text-muted-foreground/60">{message}</p>}
    </div>
  </div>
);
