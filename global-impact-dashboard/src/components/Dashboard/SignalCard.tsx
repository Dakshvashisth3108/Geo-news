import React from 'react';
import { ArrowDownRight, ArrowUpRight, Minus, Sparkles } from 'lucide-react';

import { Badge } from '../UI/primitives/Badge';
import { Card } from '../UI/primitives/Card';
import { cn, clamp, timeAgo } from '../../lib/utils';
import type { TradingSignal } from '../../lib/types';

interface SignalCardProps {
  signal: TradingSignal;
  className?: string;
}

const directionMeta = {
  LONG:    { label: 'Long',    badge: 'bull',    Icon: ArrowUpRight,   tone: 'text-bull',            glow: 'signal-glow-bull' },
  SHORT:   { label: 'Short',   badge: 'bear',    Icon: ArrowDownRight, tone: 'text-bear',            glow: 'signal-glow-bear' },
  NEUTRAL: { label: 'Neutral', badge: 'outline', Icon: Minus,          tone: 'text-muted-foreground', glow: '' },
} as const;

/** Single trading signal — used in the recent grid and the live feed. */
export const SignalCard: React.FC<SignalCardProps> = ({ signal, className }) => {
  const meta = directionMeta[signal.direction];
  const confidencePct = Math.round(clamp(signal.confidence) * 100);
  const uncertaintyPct = Math.round(clamp(signal.uncertainty) * 100);
  const gtiPct = Math.round(clamp(signal.gti, 0, 100));

  return (
    <Card className={cn('relative overflow-hidden p-5 transition-shadow hover:shadow-lg', meta.glow, className)}>
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <span className={cn('grid h-9 w-9 place-items-center rounded-md bg-secondary', meta.tone)}>
            <meta.Icon className="h-4 w-4" />
          </span>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-mono text-sm font-bold tracking-wider">{signal.asset}</span>
              <Badge variant={meta.badge as never}>{meta.label}</Badge>
            </div>
            <p className="mt-0.5 text-[11px] text-muted-foreground">{timeAgo(signal.timestamp)}</p>
          </div>
        </div>

        <div className="text-right">
          <p className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground">GTI</p>
          <p className={cn('text-2xl font-semibold tabular-nums', gtiTone(gtiPct))}>{gtiPct}</p>
        </div>
      </div>

      <p className="mt-4 text-sm leading-relaxed text-foreground/85 line-clamp-3">
        {signal.explanation}
      </p>

      <div className="mt-5 grid grid-cols-2 gap-4">
        <Metric label="Confidence" value={confidencePct} accentClass="bg-primary" />
        <Metric label="Uncertainty" value={uncertaintyPct} accentClass="bg-accent" />
      </div>

      {signal.correlated_assets.length > 0 && (
        <div className="mt-5 flex flex-wrap items-center gap-1.5 border-t border-border/60 pt-4">
          <Sparkles className="h-3.5 w-3.5 text-muted-foreground" />
          <span className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground mr-1">Correlated</span>
          {signal.correlated_assets.slice(0, 4).map((c) => (
            <Badge key={c.asset} variant="secondary" className="font-mono">
              {c.asset}
              <span
                className={cn(
                  'ml-1 text-[9px]',
                  c.expected_impact === 'LONG' && 'text-bull',
                  c.expected_impact === 'SHORT' && 'text-bear',
                )}
              >
                {c.correlation >= 0 ? '+' : ''}{c.correlation.toFixed(2)}
              </span>
            </Badge>
          ))}
        </div>
      )}
    </Card>
  );
};

const Metric: React.FC<{ label: string; value: number; accentClass: string }> = ({
  label, value, accentClass,
}) => (
  <div>
    <div className="flex items-baseline justify-between text-[10px] font-mono uppercase tracking-widest text-muted-foreground">
      <span>{label}</span>
      <span className="text-foreground tabular-nums">{value}%</span>
    </div>
    <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-secondary">
      <div className={cn('h-full rounded-full transition-[width]', accentClass)} style={{ width: `${value}%` }} />
    </div>
  </div>
);

function gtiTone(gti: number) {
  if (gti >= 75) return 'text-bear';
  if (gti >= 50) return 'text-amber-400';
  if (gti >= 25) return 'text-primary';
  return 'text-emerald-400';
}
