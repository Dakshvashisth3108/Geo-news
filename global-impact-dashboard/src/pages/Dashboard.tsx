import React, { Suspense, useState } from 'react';
import { Activity, Globe2, Layers, ShieldAlert, Target } from 'lucide-react';

import { Navbar } from '../components/UI/Navbar';
import { Card } from '../components/UI/primitives/Card';
import { GlobeModel } from '../components/Globe/GlobeScene';
import { SidePanel } from '../components/UI/SidePanel';
import { LiveFeed } from '../components/Dashboard/LiveFeed';
import { HeatmapPlaceholder } from '../components/Dashboard/HeatmapPlaceholder';
import { TimelinePlaceholder } from '../components/Dashboard/TimelinePlaceholder';

/**
 * Main dashboard.
 *
 *   Stat tiles (4)
 *   Globe (your existing GlobeModel) · LiveFeed (REST backfill + WS stream)
 *   Heatmap placeholder              · Timeline placeholder
 *
 * The globe lives inside a card now (instead of fullscreen). It still owns
 * the country-click → SidePanel flow that was in the original App.tsx.
 */
const Dashboard: React.FC = () => {
  const [selectedCountry, setSelectedCountry] = useState<string | null>(null);
  const [isPanelOpen, setIsPanelOpen] = useState(false);

  const handleCountryClick = (name: string) => {
    setSelectedCountry(name);
    setIsPanelOpen(true);
  };

  return (
    <>
      <Navbar />

      <main className="mx-auto max-w-screen-2xl space-y-6 p-6">
        {/* Header */}
        <header className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
            <p className="text-sm text-muted-foreground">
              Live geopolitical pressure mapped to actionable trading signals.
            </p>
          </div>
        </header>

        {/* Stat tiles */}
        <section className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          <StatTile icon={<Globe2 className="h-4 w-4" />}      label="Global GTI"       value="55.0" trend="+2.1 vs 1h"     tone="primary" />
          <StatTile icon={<Activity className="h-4 w-4" />}    label="Active Signals"   value="12"   trend="3 in last 5m"   tone="accent"  />
          <StatTile icon={<Layers className="h-4 w-4" />}      label="Tracked Assets"   value="48"   trend="6 sectors"                       />
          <StatTile icon={<ShieldAlert className="h-4 w-4" />} label="Critical Events"  value="2"    trend="last 24h"       tone="bear"    />
        </section>

        {/* Globe + LiveFeed */}
        <section className="grid gap-6 lg:grid-cols-3">
          <div id="signals" className="lg:col-span-2">
            <GlobePanel
              onCountryClick={handleCountryClick}
              selectedCountry={selectedCountry}
            />
          </div>
          <div className="lg:col-span-1">
            <LiveFeed />
          </div>
        </section>

        {/* Heatmap + Timeline */}
        <section className="grid gap-6 lg:grid-cols-2">
          <HeatmapPlaceholder className="min-h-[360px]" />
          <TimelinePlaceholder className="min-h-[360px]" />
        </section>
      </main>

      {/* Country detail slides over the whole dashboard. */}
      <SidePanel
        isOpen={isPanelOpen}
        countryName={selectedCountry}
        onClose={() => setIsPanelOpen(false)}
      />
    </>
  );
};

/* ----------------------------------------------------------------------
   Globe panel — wraps the existing GlobeModel in a dashboard card.
---------------------------------------------------------------------- */

interface GlobePanelProps {
  onCountryClick: (name: string) => void;
  selectedCountry: string | null;
}

const GlobePanel: React.FC<GlobePanelProps> = ({ onCountryClick, selectedCountry }) => (
  <div className="relative h-[560px] overflow-hidden rounded-[var(--radius)] border border-border/60 bg-[#000000]">
    {/* Soft radial glows behind the globe — keeps the scene from feeling flat. */}
    <div className="pointer-events-none absolute inset-0">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_50%,color-mix(in_oklab,var(--color-primary)_10%,transparent)_0%,transparent_70%)]" />
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_20%_30%,color-mix(in_oklab,var(--color-bear)_5%,transparent)_0%,transparent_45%)]" />
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_80%_70%,color-mix(in_oklab,var(--color-accent)_5%,transparent)_0%,transparent_45%)]" />
    </div>

    <Suspense fallback={null}>
      <GlobeModel onCountryClick={onCountryClick} selectedCountry={selectedCountry} />
    </Suspense>

    <div className="pointer-events-none absolute bottom-4 left-1/2 -translate-x-1/2">
      <div className="flex items-center gap-2 rounded-full border border-border bg-background/70 px-4 py-1.5 backdrop-blur-md">
        <Target size={12} className="text-primary animate-pulse" />
        <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground">
          Click a country for market impact
        </span>
      </div>
    </div>
  </div>
);

/* ----------------------------------------------------------------------
   Stat tile
---------------------------------------------------------------------- */

interface StatTileProps {
  icon: React.ReactNode;
  label: string;
  value: string;
  trend: string;
  tone?: 'default' | 'primary' | 'accent' | 'bear';
}

const StatTile: React.FC<StatTileProps> = ({ icon, label, value, trend, tone = 'default' }) => {
  const toneClass = {
    default: 'text-muted-foreground bg-secondary',
    primary: 'text-primary bg-primary/10',
    accent:  'text-accent bg-accent/10',
    bear:    'text-bear bg-bear/10',
  }[tone];

  return (
    <Card className="flex items-center justify-between p-5">
      <div>
        <p className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground">{label}</p>
        <p className="mt-1.5 text-3xl font-semibold tracking-tight tabular-nums">{value}</p>
        <p className="mt-1 text-[11px] text-muted-foreground">{trend}</p>
      </div>
      <span className={`grid h-10 w-10 place-items-center rounded-lg ${toneClass}`}>{icon}</span>
    </Card>
  );
};

export default Dashboard;
