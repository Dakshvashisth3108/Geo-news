import { Flame } from "lucide-react";

import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";

/**
 * Placeholder for the eventual asset/region tension heatmap.
 *
 * Renders a deterministic 12×6 grid of cells whose intensity comes from a
 * cheap pseudo-random function — gives a credible "data-shaped" feel until
 * the backend exposes /api/v1/heatmap.
 */
export function HeatmapPlaceholder({ className }: { className?: string }) {
  const cells = Array.from({ length: 12 * 6 }, (_, i) => ({
    id: i,
    intensity: pseudoRandom(i),
  }));

  return (
    <Card className={cn("flex h-full flex-col p-5", className)}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Flame className="h-4 w-4 text-amber-400" />
          <h2 className="text-sm font-semibold">Tension Heatmap</h2>
        </div>
        <span className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground">
          Asset × Region
        </span>
      </div>

      <div className="mt-5 grid flex-1 grid-cols-12 gap-1.5">
        {cells.map((c) => (
          <div
            key={c.id}
            className="aspect-square rounded-sm border border-border/30"
            style={{
              backgroundColor: `hsl(${239 - c.intensity * 240} 84% ${20 + c.intensity * 35}% / ${0.25 + c.intensity * 0.6})`,
            }}
          />
        ))}
      </div>

      <p className="mt-4 text-[11px] text-muted-foreground">
        Connect <code className="font-mono">/api/v1/heatmap</code> on the backend
        to render real intensity values.
      </p>
    </Card>
  );
}

function pseudoRandom(seed: number): number {
  // Cheap deterministic-ish hash → [0, 1].
  const s = Math.sin(seed * 9301 + 49297) * 233280;
  return s - Math.floor(s);
}
