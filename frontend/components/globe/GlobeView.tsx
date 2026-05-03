"use client";

/**
 * Wraps the existing globe scene in a dashboard-card-friendly container.
 * Owns the "selected country" state and the SidePanel that slides in from
 * the right edge of this card.
 *
 * Imported via `dynamic({ ssr: false })` from app/dashboard/page.tsx so
 * neither `react-globe.gl` nor any of its `window`-touching internals run
 * on the server.
 */

import { Suspense, useState } from "react";
import { Target } from "lucide-react";

import { GlobeScene } from "./GlobeScene";
import { SidePanel } from "./SidePanel";

export default function GlobeView() {
  const [selectedCountry, setSelectedCountry] = useState<string | null>(null);
  const [isPanelOpen, setIsPanelOpen] = useState(false);

  const handleCountryClick = (name: string) => {
    setSelectedCountry(name);
    setIsPanelOpen(true);
  };

  return (
    <div className="relative h-full w-full overflow-hidden rounded-[var(--radius)] border border-border/60 bg-[#000000]">
      {/* Soft radial glows behind the globe — keeps the scene from feeling flat. */}
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_50%,hsl(var(--primary)/0.10)_0%,transparent_70%)]" />
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_20%_30%,hsl(var(--bear)/0.05)_0%,transparent_45%)]" />
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_80%_70%,hsl(var(--accent)/0.05)_0%,transparent_45%)]" />
      </div>

      <Suspense fallback={null}>
        <GlobeScene
          onCountryClick={handleCountryClick}
          selectedCountry={selectedCountry}
        />
      </Suspense>

      {/* Hint pill, mirrors the original Footer component. */}
      <div className="pointer-events-none absolute bottom-4 left-1/2 -translate-x-1/2">
        <div className="flex items-center gap-2 rounded-full border border-border bg-background/70 px-4 py-1.5 backdrop-blur-md">
          <Target size={12} className="text-primary animate-pulse" />
          <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground">
            Click a country for market impact
          </span>
        </div>
      </div>

      <SidePanel
        isOpen={isPanelOpen}
        countryName={selectedCountry}
        onClose={() => setIsPanelOpen(false)}
      />
    </div>
  );
}
