import React, { useEffect, useMemo, useRef, useState } from 'react';
import { geoNaturalEarth1, geoPath } from 'd3-geo';
import { Flame } from 'lucide-react';

import { Card } from '../UI/primitives/Card';
import { cn } from '../../lib/utils';
import { api } from '../../lib/api';
import type { EventSeverity, GeopoliticalEvent } from '../../lib/types';

/**
 * Dynamic world heatmap.
 *
 * Data flow:
 *   1. Fetch the world GeoJSON (same source the 3D globe uses — browser
 *      cache dedupes between the two visualisations).
 *   2. Fetch recent GeopoliticalEvents from the backend; aggregate per
 *      country (max severity wins; signal_count = number of events).
 *   3. If the backend is unreachable or empty, fall back to a small
 *      curated mock map so the UI is never blank in dev.
 *
 * Rendering:
 *   * `d3-geo` (already a project dep) projects each polygon to SVG path
 *     data using the Natural Earth 1 projection — that's the
 *     "compromise" projection used by The Economist + most newsrooms.
 *   * Container is sized via ResizeObserver so the SVG re-fits when the
 *     dashboard grid resizes.
 */

// --- Constants -------------------------------------------------------------

const WORLD_GEOJSON_URL =
  'https://raw.githubusercontent.com/holtzy/D3-graph-gallery/master/DATA/world.geojson';

// Severity → tension contribution (max-wins per country).
const SEVERITY_TO_TENSION: Record<EventSeverity, number> = {
  LOW: 25, MEDIUM: 50, HIGH: 75, CRITICAL: 100,
};

// Map ISO 3166-1 alpha-2 codes (used by the backend's GeopoliticalEvent.countries)
// to the country names the Holtzy GeoJSON uses on `feature.properties.name`.
// Coverage is intentionally focused on the markets we care about — extend as
// new asset/country pairs come online.
const ISO2_TO_GEONAME: Record<string, string> = {
  US: 'United States of America',
  RU: 'Russia',
  UA: 'Ukraine',
  CN: 'China',
  IN: 'India',
  IR: 'Iran',
  IL: 'Israel',
  SA: 'Saudi Arabia',
  GB: 'United Kingdom',
  DE: 'Germany',
  FR: 'France',
  IT: 'Italy',
  ES: 'Spain',
  JP: 'Japan',
  KR: 'South Korea',
  KP: 'North Korea',
  CA: 'Canada',
  AU: 'Australia',
  BR: 'Brazil',
  MX: 'Mexico',
  TR: 'Turkey',
  EG: 'Egypt',
  PK: 'Pakistan',
  AF: 'Afghanistan',
  SY: 'Syria',
  IQ: 'Iraq',
  YE: 'Yemen',
  LB: 'Lebanon',
  VE: 'Venezuela',
  NG: 'Nigeria',
  ZA: 'South Africa',
  ID: 'Indonesia',
  TH: 'Thailand',
  VN: 'Vietnam',
  PH: 'Philippines',
  TW: 'Taiwan',
  AR: 'Argentina',
  CL: 'Chile',
  CO: 'Colombia',
};

// --- Types -----------------------------------------------------------------

interface CountryTension {
  name: string;        // matches feature.properties.name
  tension: number;     // [0, 100]
  signalCount: number;
}

interface HeatmapProps {
  className?: string;
  /** Called with the country name when the user clicks a polygon. */
  onCountryClick?: (countryName: string) => void;
}

// --- Helpers ---------------------------------------------------------------

function tensionFill(tension: number): string {
  // Tuned against the dashboard's dark surface so countries pop without
  // washing out the rest of the UI.
  if (tension <= 0) return 'rgba(99, 102, 241, 0.07)';
  if (tension < 30) return 'rgba(16, 185, 129, 0.40)';   // emerald
  if (tension < 50) return 'rgba(245, 158, 11, 0.55)';   // amber
  if (tension < 75) return 'rgba(244, 114, 91, 0.65)';   // orange
  return 'rgba(244, 63, 94, 0.85)';                       // rose / critical
}

function generateMockTensions(): Map<string, CountryTension> {
  // Deterministic so we get stable demo screenshots.
  const seed: Array<[string, number, number]> = [
    ['Russia', 95, 12],
    ['Ukraine', 90, 8],
    ['Iran', 82, 6],
    ['Israel', 78, 5],
    ['Saudi Arabia', 60, 4],
    ['China', 65, 9],
    ['United States of America', 55, 14],
    ['Germany', 45, 4],
    ['India', 40, 3],
    ['United Kingdom', 35, 3],
    ['Venezuela', 55, 2],
    ['Turkey', 50, 3],
    ['Yemen', 70, 4],
    ['Syria', 72, 3],
    ['Iraq', 65, 3],
    ['Brazil', 28, 2],
    ['South Korea', 30, 2],
    ['North Korea', 75, 3],
  ];
  const out = new Map<string, CountryTension>();
  for (const [name, tension, signalCount] of seed) {
    out.set(name, { name, tension, signalCount });
  }
  return out;
}

function aggregateEventsToTensions(
  events: GeopoliticalEvent[],
): Map<string, CountryTension> {
  const out = new Map<string, CountryTension>();
  for (const event of events) {
    const score = SEVERITY_TO_TENSION[event.severity] ?? 0;
    for (const iso of event.countries ?? []) {
      const geoName = ISO2_TO_GEONAME[iso.toUpperCase()] ?? null;
      if (!geoName) continue;       // skip unknown ISO codes
      const existing = out.get(geoName) ?? { name: geoName, tension: 0, signalCount: 0 };
      existing.tension = Math.max(existing.tension, score);
      existing.signalCount += 1;
      out.set(geoName, existing);
    }
  }
  return out;
}

// --- Component -------------------------------------------------------------

export const GeopoliticalHeatmap: React.FC<HeatmapProps> = ({ className, onCountryClick }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ width: 0, height: 0 });
  const [geoData, setGeoData] = useState<any>(null);
  const [tensions, setTensions] = useState<Map<string, CountryTension>>(new Map());
  const [hovered, setHovered] = useState<{ name: string; tension: number; count: number; x: number; y: number } | null>(null);

  // Track container size so the projection always fits its parent box.
  useEffect(() => {
    if (!containerRef.current) return;
    const el = containerRef.current;
    const update = () => setSize({ width: el.clientWidth, height: el.clientHeight });
    update();
    const ro = new ResizeObserver(update);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  // Fetch world topology (browser HTTP cache dedupes vs the 3D globe).
  useEffect(() => {
    let cancelled = false;
    fetch(WORLD_GEOJSON_URL)
      .then((res) => res.json())
      .then((data) => { if (!cancelled) setGeoData(data); })
      .catch(() => {
        // Network blocked / offline — leave geoData null so we render an
        // empty card with the legend rather than crashing.
      });
    return () => { cancelled = true; };
  }, []);

  // Fetch events and aggregate to per-country tensions.
  useEffect(() => {
    let cancelled = false;
    api.events.list({ limit: 200 })
      .then((events) => {
        if (cancelled) return;
        const aggregated = aggregateEventsToTensions(events);
        setTensions(aggregated.size > 0 ? aggregated : generateMockTensions());
      })
      .catch(() => { if (!cancelled) setTensions(generateMockTensions()); });
    return () => { cancelled = true; };
  }, []);

  // Build a path generator scoped to the current container size.
  const { pathGen, spherePath } = useMemo(() => {
    if (!size.width || !size.height || !geoData) {
      return { pathGen: null as ReturnType<typeof geoPath> | null, spherePath: '' };
    }
    const projection = geoNaturalEarth1().fitSize([size.width, size.height], geoData as any);
    const gen = geoPath(projection as any);
    return {
      pathGen: gen,
      spherePath: gen({ type: 'Sphere' } as any) ?? '',
    };
  }, [geoData, size]);

  // Mouse handlers — record svg-relative coordinates for the tooltip.
  const handlePathEnter = (e: React.MouseEvent<SVGPathElement>, name: string) => {
    const rect = containerRef.current?.getBoundingClientRect();
    if (!rect) return;
    const t = tensions.get(name);
    setHovered({
      name: name || 'Unknown',
      tension: t?.tension ?? 0,
      count: t?.signalCount ?? 0,
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
    });
  };

  const handlePathMove = (e: React.MouseEvent<SVGPathElement>) => {
    const rect = containerRef.current?.getBoundingClientRect();
    if (!rect) return;
    setHovered((h) => h && { ...h, x: e.clientX - rect.left, y: e.clientY - rect.top });
  };

  return (
    <Card className={cn('flex h-full flex-col p-5', className)}>
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Flame className="h-4 w-4 text-amber-400" />
          <h2 className="text-sm font-semibold">Geopolitical Tension Heatmap</h2>
        </div>
        <span className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground">
          Severity-weighted · last 200 events
        </span>
      </div>

      <div
        ref={containerRef}
        className="relative flex-1 overflow-hidden rounded-md border border-border/40 bg-card/40"
      >
        {pathGen && geoData && size.width > 0 && (
          <svg width={size.width} height={size.height} className="block">
            {/* Sphere — gives the map a defined edge against the dark card. */}
            <path d={spherePath} fill="rgba(2, 6, 23, 1)" stroke="rgba(99, 102, 241, 0.20)" strokeWidth={0.5} />

            {/* Country polygons */}
            {(geoData.features as any[]).map((feature, i) => {
              const name: string = feature.properties?.name ?? '';
              const t = tensions.get(name);
              const tension = t?.tension ?? 0;
              const d = pathGen(feature);
              if (!d) return null;
              return (
                <path
                  key={`${name}-${i}`}
                  d={d}
                  fill={tensionFill(tension)}
                  stroke="rgba(255,255,255,0.06)"
                  strokeWidth={0.4}
                  className="cursor-pointer transition-[fill] duration-200 hover:fill-white/30"
                  onMouseEnter={(e) => handlePathEnter(e, name)}
                  onMouseMove={handlePathMove}
                  onMouseLeave={() => setHovered(null)}
                  onClick={() => onCountryClick?.(name)}
                />
              );
            })}
          </svg>
        )}

        {/* Tooltip */}
        {hovered && (
          <div
            className="pointer-events-none absolute z-10 rounded-md border border-border bg-card/90 px-3 py-1.5 text-xs shadow-lg backdrop-blur-md"
            style={{
              left: Math.min(hovered.x + 12, (size.width || 0) - 180),
              top: Math.min(hovered.y + 12, (size.height || 0) - 80),
            }}
          >
            <div className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground">
              Tension
            </div>
            <div className="font-semibold">{hovered.name}</div>
            <div className="mt-0.5 text-[11px] text-muted-foreground tabular-nums">
              {hovered.tension > 0
                ? `${hovered.tension}/100 · ${hovered.count} signal${hovered.count === 1 ? '' : 's'}`
                : 'no recent signals'}
            </div>
          </div>
        )}
      </div>

      {/* Legend */}
      <div className="mt-4 flex flex-wrap items-center gap-3">
        <span className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground">
          Tension scale
        </span>
        {[
          { label: 'None', tension: 0 },
          { label: 'Low', tension: 20 },
          { label: 'Med', tension: 40 },
          { label: 'High', tension: 60 },
          { label: 'Crit', tension: 90 },
        ].map((s) => (
          <span
            key={s.label}
            className="inline-flex items-center gap-1.5 text-[10px] font-mono uppercase tracking-widest text-muted-foreground"
          >
            <span
              className="h-2.5 w-2.5 rounded-sm border border-border/50"
              style={{ backgroundColor: tensionFill(s.tension) }}
            />
            {s.label}
          </span>
        ))}
      </div>
    </Card>
  );
};
