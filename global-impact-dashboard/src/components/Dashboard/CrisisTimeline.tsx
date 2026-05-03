import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Clock, X } from 'lucide-react';

import { Card } from '../UI/primitives/Card';
import { cn } from '../../lib/utils';
import { api } from '../../lib/api';
import type { EventSeverity, EventType, GeopoliticalEvent } from '../../lib/types';

/**
 * Horizontally-scrollable crisis timeline.
 *
 * Interactions:
 *   * Drag-to-pan       (mouse + touch via native scroll)
 *   * Wheel-to-pan      (vertical wheel scrolls the timeline horizontally)
 *   * Range switcher    (24h / 7d / 30d) controls both filter + zoom
 *   * Hover a marker    -> detail card
 *   * Click a marker    -> pin the detail card (Close button to release)
 *
 * A small drag-vs-click discriminator suppresses the click handler when
 * the user was actually panning, so dragging across the timeline never
 * accidentally pins a random event.
 */

// --- Constants -------------------------------------------------------------

const SEVERITY_COLORS: Record<EventSeverity, string> = {
  LOW: '#10b981',       // emerald
  MEDIUM: '#f59e0b',    // amber
  HIGH: '#f97316',      // orange
  CRITICAL: '#ef4444',  // red
};

type Range = '24h' | '7d' | '30d';

const RANGE_HOURS: Record<Range, number> = {
  '24h': 24,
  '7d': 24 * 7,
  '30d': 24 * 30,
};

// Wider tracks for shorter ranges so events don't pile on top of each other.
const PX_PER_HOUR: Record<Range, number> = {
  '24h': 90,
  '7d': 28,
  '30d': 10,
};

// Drag dead-zone: movement under this many px is treated as a click.
const DRAG_THRESHOLD = 4;

// --- Helpers ---------------------------------------------------------------

function generateMockEvents(): GeopoliticalEvent[] {
  const now = Date.now();
  const types: EventType[] = [
    'WAR', 'CONFLICT', 'SANCTION', 'ELECTION', 'POLICY',
    'TERRORISM', 'NATURAL_DISASTER', 'ECONOMIC', 'DIPLOMATIC',
  ];
  const severities: EventSeverity[] = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'];
  const titles = [
    'Border skirmish reported',
    'OPEC+ statement on production cuts',
    'New sanctions package proposed',
    'CPI release exceeds forecast',
    'Naval drill announced',
    'Election poll update',
    'Coastal earthquake reported',
    'Diplomatic summit concluded',
    'Cyberattack on regional banks',
    'Trade deal renewed',
    'Pipeline outage confirmed',
    'Embassy attacked',
    'Oil tanker seized',
    'Currency intervention announced',
    'Cabinet reshuffle',
    'Parliamentary inquiry opened',
    'Stock circuit breaker triggered',
    'Coastal flooding worsens',
    'Strike action expands',
    'Court rules on energy policy',
  ];
  return titles.map((title, i) => {
    const offsetHours = (i / titles.length) * 24 * 7; // spread across last 7d
    const occurred = new Date(now - offsetHours * 3600_000).toISOString();
    return {
      id: `mock-${i}`,
      title,
      summary: `Mock event #${i + 1} — replace with real /api/v1/events data once the backend is reachable.`,
      event_type: types[i % types.length],
      severity: severities[i % severities.length],
      region: null,
      countries: [],
      source: null,
      source_url: null,
      occurred_at: occurred,
      ingested_at: occurred,
    };
  });
}

function formatTickLabel(date: Date, range: Range): string {
  if (range === '24h') {
    return `${String(date.getHours()).padStart(2, '0')}:00`;
  }
  // For 7d and 30d, MM/DD is dense enough.
  return `${date.getMonth() + 1}/${date.getDate()}`;
}

// --- Component -------------------------------------------------------------

interface CrisisTimelineProps {
  className?: string;
}

export const CrisisTimeline: React.FC<CrisisTimelineProps> = ({ className }) => {
  const [events, setEvents] = useState<GeopoliticalEvent[]>([]);
  const [range, setRange] = useState<Range>('7d');
  const [hovered, setHovered] = useState<GeopoliticalEvent | null>(null);
  const [selected, setSelected] = useState<GeopoliticalEvent | null>(null);

  const scrollRef = useRef<HTMLDivElement>(null);
  // Tracks the active drag — refs (not state) so we don't trigger renders on
  // every mousemove.
  const drag = useRef({ x: 0, scroll: 0, active: false, moved: false });

  // Fetch events on mount.
  useEffect(() => {
    let cancelled = false;
    api.events.list({ limit: 200 })
      .then((data) => {
        if (cancelled) return;
        setEvents(data.length > 0 ? data : generateMockEvents());
      })
      .catch(() => { if (!cancelled) setEvents(generateMockEvents()); });
    return () => { cancelled = true; };
  }, []);

  // After range change, scroll to the present (right edge) so the most
  // recent events are visible immediately.
  useEffect(() => {
    if (!scrollRef.current) return;
    const el = scrollRef.current;
    requestAnimationFrame(() => {
      el.scrollLeft = el.scrollWidth - el.clientWidth;
    });
  }, [range, events.length]);

  // --- Visible window + layout sizing ------------------------------------

  const totalHours = RANGE_HOURS[range];
  const totalWidth = totalHours * PX_PER_HOUR[range];

  const visibleEvents = useMemo(() => {
    const cutoff = Date.now() - totalHours * 3600_000;
    return events
      .filter((e) => new Date(e.occurred_at).getTime() >= cutoff)
      .sort(
        (a, b) =>
          new Date(a.occurred_at).getTime() - new Date(b.occurred_at).getTime(),
      );
  }, [events, totalHours]);

  // Tick layout — 1h / 12h / 24h depending on range.
  const tickStep = range === '24h' ? 1 : range === '7d' ? 12 : 24;
  const ticks = useMemo(
    () => Array.from({ length: Math.floor(totalHours / tickStep) + 1 }, (_, i) => i * tickStep),
    [totalHours, tickStep],
  );

  // --- Drag-to-pan handlers ----------------------------------------------

  const onMouseDown = (e: React.MouseEvent) => {
    if (!scrollRef.current) return;
    drag.current = {
      x: e.pageX,
      scroll: scrollRef.current.scrollLeft,
      active: true,
      moved: false,
    };
    // Cursor change is imperative — the ref doesn't trigger re-renders.
    scrollRef.current.style.cursor = 'grabbing';
  };

  const onMouseMove = (e: React.MouseEvent) => {
    if (!drag.current.active || !scrollRef.current) return;
    const dx = e.pageX - drag.current.x;
    if (Math.abs(dx) > DRAG_THRESHOLD) drag.current.moved = true;
    scrollRef.current.scrollLeft = drag.current.scroll - dx;
  };

  const endDrag = () => {
    drag.current.active = false;
    if (scrollRef.current) scrollRef.current.style.cursor = 'grab';
  };

  // Vertical wheel translates to horizontal scroll. Horizontal wheel
  // (trackpad) is left alone so native handling still works.
  const onWheel = (e: React.WheelEvent) => {
    if (!scrollRef.current) return;
    if (Math.abs(e.deltaY) > Math.abs(e.deltaX)) {
      scrollRef.current.scrollLeft += e.deltaY;
    }
  };

  const onMarkerClick = (event: GeopoliticalEvent, e: React.MouseEvent) => {
    // Suppress click if user was panning across the timeline.
    if (drag.current.moved) return;
    e.stopPropagation();
    setSelected((cur) => (cur?.id === event.id ? null : event));
  };

  // The card to show — selected pin wins over hover.
  const detail = selected ?? hovered;

  return (
    <Card className={cn('flex h-full flex-col p-5', className)}>
      {/* Header */}
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Clock className="h-4 w-4 text-primary" />
          <h2 className="text-sm font-semibold">Crisis Timeline</h2>
        </div>
        <RangeSwitcher value={range} onChange={setRange} />
      </div>

      {/* Scroll viewport */}
      <div
        ref={scrollRef}
        className="relative flex-1 overflow-x-auto overflow-y-hidden cursor-grab select-none"
        onMouseDown={onMouseDown}
        onMouseMove={onMouseMove}
        onMouseUp={endDrag}
        onMouseLeave={endDrag}
        onWheel={onWheel}
      >
        <div className="relative h-full" style={{ width: totalWidth }}>
          {/* Axis */}
          <div className="absolute left-0 right-0 top-1/2 h-px -translate-y-1/2 bg-border" />

          {/* Tick marks */}
          {ticks.map((hour) => {
            const left = (hour / totalHours) * totalWidth;
            const tickDate = new Date(Date.now() - (totalHours - hour) * 3600_000);
            return (
              <div
                key={hour}
                className="absolute top-1/2 flex -translate-y-1/2 flex-col items-center pointer-events-none"
                style={{ left }}
              >
                <span className="h-2 w-px bg-border" />
                <span className="mt-1 whitespace-nowrap text-[10px] font-mono text-muted-foreground">
                  {formatTickLabel(tickDate, range)}
                </span>
              </div>
            );
          })}

          {/* Event markers */}
          {visibleEvents.map((event) => {
            const eventTimeMs = new Date(event.occurred_at).getTime();
            const offsetHours = (Date.now() - eventTimeMs) / 3600_000;
            const left = ((totalHours - offsetHours) / totalHours) * totalWidth;
            const color = SEVERITY_COLORS[event.severity] ?? '#94a3b8';
            const isSelected = selected?.id === event.id;
            return (
              <button
                type="button"
                key={event.id}
                style={{ left }}
                className={cn(
                  'group absolute top-1/2 -translate-x-1/2 -translate-y-1/2',
                  'transition-transform hover:scale-150',
                )}
                onMouseEnter={() => setHovered(event)}
                onMouseLeave={() => setHovered(null)}
                onClick={(e) => onMarkerClick(event, e)}
                aria-label={event.title}
              >
                <span
                  className={cn(
                    'block h-3 w-3 rounded-full ring-4 ring-background transition-shadow',
                    isSelected && 'shadow-[0_0_0_2px_var(--color-primary)]',
                  )}
                  style={{ backgroundColor: color }}
                />
              </button>
            );
          })}
        </div>
      </div>

      {/* Legend */}
      <div className="mt-3 flex flex-wrap gap-3 border-t border-border/40 pt-3">
        {(Object.keys(SEVERITY_COLORS) as EventSeverity[]).map((sev) => (
          <span
            key={sev}
            className="inline-flex items-center gap-1.5 text-[10px] font-mono uppercase tracking-widest text-muted-foreground"
          >
            <span
              className="h-2 w-2 rounded-full"
              style={{ backgroundColor: SEVERITY_COLORS[sev] }}
            />
            {sev}
          </span>
        ))}
        <span className="ml-auto text-[10px] font-mono uppercase tracking-widest text-muted-foreground">
          {visibleEvents.length} events · drag or scroll to pan
        </span>
      </div>

      {/* Detail card (hover preview OR pinned selection) */}
      {detail && <DetailCard detail={detail} pinned={!!selected} onClose={() => setSelected(null)} />}
    </Card>
  );
};

// --- Sub-components --------------------------------------------------------

const RangeSwitcher: React.FC<{ value: Range; onChange: (r: Range) => void }> = ({ value, onChange }) => (
  <div className="flex items-center gap-1 rounded-md border border-border bg-card/60 p-0.5">
    {(['24h', '7d', '30d'] as Range[]).map((r) => (
      <button
        key={r}
        type="button"
        onClick={() => onChange(r)}
        className={cn(
          'rounded px-2 py-0.5 text-[10px] font-mono uppercase tracking-widest transition-colors',
          value === r
            ? 'bg-primary text-primary-foreground'
            : 'text-muted-foreground hover:text-foreground',
        )}
      >
        {r}
      </button>
    ))}
  </div>
);

const DetailCard: React.FC<{ detail: GeopoliticalEvent; pinned: boolean; onClose: () => void }> = ({
  detail, pinned, onClose,
}) => (
  <div className="mt-3 rounded-md border border-border bg-card/70 p-3 backdrop-blur-md">
    <div className="flex items-start justify-between gap-3">
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <span
            className="h-2 w-2 shrink-0 rounded-full"
            style={{ backgroundColor: SEVERITY_COLORS[detail.severity] }}
          />
          <span className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground">
            {detail.event_type.replace('_', ' ').toLowerCase()}
          </span>
          <span className="text-[10px] font-mono text-muted-foreground">
            · {new Date(detail.occurred_at).toLocaleString()}
          </span>
        </div>
        <h3 className="mt-1 text-sm font-semibold leading-tight">{detail.title}</h3>
        <p className="mt-1 line-clamp-2 text-xs text-muted-foreground">
          {detail.summary}
        </p>
      </div>
      {pinned && (
        <button
          type="button"
          onClick={onClose}
          className="inline-flex items-center gap-1 rounded-md border border-border bg-card px-2 py-1 text-[10px] font-mono uppercase tracking-widest text-muted-foreground hover:text-foreground"
        >
          <X className="h-3 w-3" />
          Close
        </button>
      )}
    </div>
  </div>
);
