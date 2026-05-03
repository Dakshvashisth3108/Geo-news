"use client";

/**
 * Main dashboard. Marked `"use client"` so we can use `next/dynamic`
 * with `ssr: false` to load the WebGL globe (it touches `window` at
 * import time via react-globe.gl).
 *
 * Layout:
 *   ┌──────────────────────────────────────────────────┐
 *   │ Stat tiles                                        │
 *   ├───────────────────────────┬──────────────────────┤
 *   │ Globe                     │ LiveFeed (WS-driven) │
 *   ├───────────────────────────┴──────────────────────┤
 *   │ Heatmap placeholder       │ Timeline placeholder │
 *   └──────────────────────────────────────────────────┘
 */

import dynamic from "next/dynamic";
import { Activity, Globe2, Layers, ShieldAlert } from "lucide-react";

import { Navbar } from "@/components/layout/Navbar";
import { LiveFeed } from "@/components/dashboard/LiveFeed";
import { HeatmapPlaceholder } from "@/components/dashboard/HeatmapPlaceholder";
import { TimelinePlaceholder } from "@/components/dashboard/TimelinePlaceholder";
import { Card } from "@/components/ui/card";

// react-globe.gl + three need DOM APIs at import time — kill SSR for them.
const GlobeView = dynamic(() => import("@/components/globe/GlobeView"), {
  ssr: false,
  loading: () => (
    <div className="grid h-full w-full place-items-center rounded-[var(--radius)] border border-border/60 bg-card/40">
      <div className="text-center">
        <div className="mx-auto h-10 w-10 animate-spin rounded-full border-2 border-primary border-t-transparent" />
        <p className="mt-4 text-xs font-mono uppercase tracking-widest text-muted-foreground">
          Initialising globe…
        </p>
      </div>
    </div>
  ),
});

export default function DashboardPage() {
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
          <StatTile
            icon={<Globe2 className="h-4 w-4" />}
            label="Global GTI"
            value="55.0"
            trend="+2.1 vs 1h"
            tone="primary"
          />
          <StatTile
            icon={<Activity className="h-4 w-4" />}
            label="Active Signals"
            value="12"
            trend="3 in last 5m"
            tone="accent"
          />
          <StatTile
            icon={<Layers className="h-4 w-4" />}
            label="Tracked Assets"
            value="48"
            trend="6 sectors"
          />
          <StatTile
            icon={<ShieldAlert className="h-4 w-4" />}
            label="Critical Events"
            value="2"
            trend="last 24h"
            tone="bear"
          />
        </section>

        {/* Globe + LiveFeed */}
        <section className="grid gap-6 lg:grid-cols-3">
          <div id="signals" className="lg:col-span-2">
            <div className="h-[560px]">
              <GlobeView />
            </div>
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
    </>
  );
}

function StatTile({
  icon,
  label,
  value,
  trend,
  tone = "default",
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  trend: string;
  tone?: "default" | "primary" | "accent" | "bear";
}) {
  const toneClass = {
    default: "text-muted-foreground bg-secondary",
    primary: "text-primary bg-primary/10",
    accent:  "text-accent bg-accent/10",
    bear:    "text-[hsl(var(--bear))] bg-[hsl(var(--bear)/0.10)]",
  }[tone];

  return (
    <Card className="flex items-center justify-between p-5">
      <div>
        <p className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground">
          {label}
        </p>
        <p className="mt-1.5 text-3xl font-semibold tracking-tight tabular-nums">
          {value}
        </p>
        <p className="mt-1 text-[11px] text-muted-foreground">{trend}</p>
      </div>
      <span className={`grid h-10 w-10 place-items-center rounded-lg ${toneClass}`}>
        {icon}
      </span>
    </Card>
  );
}
