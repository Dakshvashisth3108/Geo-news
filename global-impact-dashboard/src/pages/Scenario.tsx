import React, { useState } from 'react';
import { AlertTriangle, Beaker, Loader2, Sparkles, Wand2 } from 'lucide-react';

import { Navbar } from '../components/UI/Navbar';
import { Button } from '../components/UI/primitives/Button';
import { Badge } from '../components/UI/primitives/Badge';
import { Card } from '../components/UI/primitives/Card';
import { SignalCard } from '../components/Dashboard/SignalCard';

import { api, APIError } from '../lib/api';
import { cn } from '../lib/utils';
import type {
  EventSeverity,
  ScenarioSimulateResponse,
  TradingSignal,
} from '../lib/types';

/**
 * What-If Scenario Simulator.
 *
 * Glue page over the FastAPI /scenarios/simulate endpoint:
 *   1. User types/picks a hypothetical event in plain English.
 *   2. We POST to the backend; it composes NLP + correlation engine
 *      and returns extracted facts, projected impact, and a narrative.
 *   3. We render facts as chips, the projection as a SignalCard, and
 *      the narrative as a single paragraph.
 *
 * UI never blocks on a missing backend or NLP deps — the API returns
 * a heuristic-derived response in those cases (extracted.source === 'heuristic').
 */

const PRESETS: string[] = [
  'Russian forces strike Ukrainian wheat depot in Odessa, severe casualties reported overnight.',
  'Iranian missiles land near a Saudi Arabian refinery; OPEC+ calls an emergency session.',
  'United States announces sweeping new sanctions on Russian energy and banking exports.',
  'Magnitude 7.2 earthquake hits Tokyo; Bank of Japan announces emergency liquidity measures.',
  'Surprise opposition victory in Indian general election sends rupee sharply lower.',
  'Major peace deal signed between Israel and neighbouring states, oil drops on supply relief.',
];

const SEVERITY_OPTIONS: Array<EventSeverity | ''> = ['', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'];

const Scenario: React.FC = () => {
  const [text, setText] = useState('');
  const [severityHint, setSeverityHint] = useState<EventSeverity | ''>('');
  const [regionHint, setRegionHint] = useState('');
  const [primaryOverride, setPrimaryOverride] = useState('');

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ScenarioSimulateResponse | null>(null);

  const submit = async () => {
    if (text.trim().length < 10) return;
    setLoading(true);
    setError(null);
    try {
      const data = await api.scenarios.simulate({
        text: text.trim(),
        severity_hint: severityHint || undefined,
        region_hint: regionHint.trim() || undefined,
        primary_asset_override: primaryOverride.trim() || undefined,
      });
      setResult(data);
    } catch (e) {
      setError(e instanceof APIError ? `${e.status}: ${e.message}` : (e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const onKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Cmd/Ctrl + Enter submits — power users will appreciate this.
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
      e.preventDefault();
      submit();
    }
  };

  return (
    <>
      <Navbar />
      <main className="mx-auto max-w-screen-xl space-y-6 p-6">
        <header>
          <div className="flex items-center gap-2">
            <span className="grid h-9 w-9 place-items-center rounded-md bg-primary/15 text-primary">
              <Beaker className="h-5 w-5" />
            </span>
            <h1 className="text-2xl font-semibold tracking-tight">
              What-If Scenario Simulator
            </h1>
          </div>
          <p className="mt-2 text-sm text-muted-foreground max-w-2xl">
            Sketch a hypothetical geopolitical event in plain English. The engine
            extracts structured facts (NLP) and projects the asset impact based on
            historical correlation patterns.
          </p>
        </header>

        {/* ------------------ Input ------------------ */}
        <Card className="p-5">
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder="e.g. 'Russian forces strike Ukrainian wheat depot in Odessa, severe casualties reported.'"
            className="min-h-[120px] w-full resize-y rounded-md border border-border bg-card/40 p-3 text-sm leading-relaxed focus:outline-none focus:ring-2 focus:ring-ring"
          />

          <div className="mt-3 flex flex-wrap items-center gap-2">
            <select
              value={severityHint}
              onChange={(e) => setSeverityHint(e.target.value as EventSeverity | '')}
              className="rounded-md border border-border bg-card/40 px-2 py-1.5 text-xs"
              title="Force a severity instead of letting the engine infer one"
            >
              {SEVERITY_OPTIONS.map((s) => (
                <option key={s || 'auto'} value={s}>
                  {s ? `Severity: ${s}` : 'Severity: auto'}
                </option>
              ))}
            </select>

            <input
              type="text"
              value={regionHint}
              onChange={(e) => setRegionHint(e.target.value)}
              placeholder="Region hint (e.g. 'middle east')"
              className="rounded-md border border-border bg-card/40 px-2 py-1.5 text-xs w-[180px]"
            />

            <input
              type="text"
              value={primaryOverride}
              onChange={(e) => setPrimaryOverride(e.target.value.toUpperCase())}
              placeholder="Pin primary asset (e.g. BRENT)"
              className="rounded-md border border-border bg-card/40 px-2 py-1.5 text-xs w-[200px] font-mono"
            />

            <span className="ml-auto text-[10px] font-mono uppercase tracking-widest text-muted-foreground hidden sm:inline">
              ⌘/Ctrl + ↵
            </span>
            <Button
              onClick={submit}
              disabled={loading || text.trim().length < 10}
              className="min-w-[180px]"
            >
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" /> Simulating…
                </>
              ) : (
                <>
                  <Wand2 className="h-4 w-4" /> Run Simulation
                </>
              )}
            </Button>
          </div>

          {/* Presets */}
          <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-border/40 pt-3">
            <span className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground">
              Try
            </span>
            {PRESETS.map((p, i) => (
              <button
                key={i}
                type="button"
                onClick={() => setText(p)}
                className="rounded-full border border-border bg-card px-2.5 py-0.5 text-[11px] text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
                title={p}
              >
                {p.length > 60 ? p.slice(0, 60) + '…' : p}
              </button>
            ))}
          </div>
        </Card>

        {/* ------------------ Error ------------------ */}
        {error && (
          <Card className="border-destructive/50 p-4">
            <div className="flex items-start gap-2 text-sm text-destructive">
              <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />
              <div>
                <p className="font-semibold">Simulation failed</p>
                <p className="mt-0.5 text-xs">{error}</p>
              </div>
            </div>
          </Card>
        )}

        {/* ------------------ Results ------------------ */}
        {result && <Results data={result} />}
      </main>
    </>
  );
};

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

const Results: React.FC<{ data: ScenarioSimulateResponse }> = ({ data }) => {
  // Synthesise a TradingSignal from the projection so we can reuse the
  // SignalCard component verbatim instead of writing another card variant.
  const fakeSignal: TradingSignal = {
    id: 'projection',
    asset: data.projection.primary_asset,
    direction: data.projection.direction,
    confidence: data.projection.confidence,
    uncertainty: data.projection.uncertainty,
    gti: data.projection.gti,
    explanation: data.projection.reasoning,
    correlated_assets: data.projection.correlated_assets,
    event_id: null,
    timestamp: new Date().toISOString(),
  };

  return (
    <section className="space-y-6">
      <div className="grid gap-6 lg:grid-cols-2">
        <ExtractedFactsCard data={data} />
        <Card className="p-5">
          <h2 className="text-sm font-semibold mb-3">Primary Projection</h2>
          <SignalCard signal={fakeSignal} />
        </Card>
      </div>

      <Card className="p-5">
        <div className="flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-accent" />
          <h2 className="text-sm font-semibold">Narrative</h2>
        </div>
        <p className="mt-3 text-sm leading-relaxed text-foreground/85">
          {data.narrative}
        </p>
      </Card>
    </section>
  );
};

const ExtractedFactsCard: React.FC<{ data: ScenarioSimulateResponse }> = ({ data }) => {
  const f = data.extracted;
  const heuristic = f.source === 'heuristic';

  return (
    <Card className="p-5">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold">Extracted Facts</h2>
        <Badge variant={heuristic ? 'outline' : 'accent'} className="font-mono">
          {f.source}
        </Badge>
      </div>

      {heuristic && (
        <p className="mt-2 text-[11px] text-muted-foreground">
          Running on the keyword fallback — install <code className="font-mono">torch</code>,
          {' '}<code className="font-mono">transformers</code>, and{' '}
          <code className="font-mono">spacy</code> for the full NLP pipeline.
        </p>
      )}

      <div className="mt-4 grid grid-cols-2 gap-x-6 gap-y-3 text-sm">
        <Field label="Event type" value={f.event_type.replace('_', ' ')} />
        <Field label="Severity" value={f.severity} valueClass={severityTone(f.severity)} />
        <Field
          label="Sentiment"
          value={`${f.sentiment_label} (${f.sentiment_polarity >= 0 ? '+' : ''}${f.sentiment_polarity.toFixed(2)})`}
        />
        <Field label="NLP GTI" value={`${f.gti_nlp.toFixed(0)} / 100`} />
      </div>

      <ChipRow label="Countries" values={f.countries_iso} mono />
      <ChipRow label="Assets in text" values={f.assets_mentioned} mono />
      <ChipRow label="People" values={f.persons} max={6} />
      <ChipRow label="Organizations" values={f.organizations} max={6} />

      {data.partial_failures.length > 0 && (
        <p className="mt-3 text-[11px] text-muted-foreground">
          Degraded stages:{' '}
          <span className="font-mono">{data.partial_failures.join(', ')}</span>
        </p>
      )}
    </Card>
  );
};

const Field: React.FC<{ label: string; value: string; valueClass?: string }> = ({
  label, value, valueClass,
}) => (
  <div>
    <div className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground">
      {label}
    </div>
    <div className={cn('mt-0.5 font-medium', valueClass)}>{value}</div>
  </div>
);

const ChipRow: React.FC<{ label: string; values: string[]; max?: number; mono?: boolean }> = ({
  label, values, max = 12, mono = false,
}) => {
  if (values.length === 0) return null;
  const visible = values.slice(0, max);
  const more = values.length - visible.length;
  return (
    <div className="mt-3">
      <div className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground">
        {label}
      </div>
      <div className="mt-1.5 flex flex-wrap gap-1.5">
        {visible.map((v) => (
          <Badge key={v} variant="secondary" className={cn(mono && 'font-mono')}>
            {v}
          </Badge>
        ))}
        {more > 0 && (
          <span className="text-[11px] text-muted-foreground self-center">+{more}</span>
        )}
      </div>
    </div>
  );
};

function severityTone(severity: EventSeverity): string {
  return {
    LOW: 'text-bull',
    MEDIUM: 'text-amber-400',
    HIGH: 'text-orange-400',
    CRITICAL: 'text-bear',
  }[severity];
}

export default Scenario;
