"use client";

/**
 * Ported from `global-impact-dashboard/src/components/UI/SidePanel.tsx`.
 * Slides in when the user clicks a country on the globe.
 */

import { motion, AnimatePresence } from "framer-motion";
import { TrendingUp, Crosshair, X } from "lucide-react";

import { cn } from "@/lib/utils";

interface SidePanelProps {
  isOpen: boolean;
  onClose: () => void;
  countryName: string | null;
}

const ASSETS = [
  { name: "HSI",    value: "16.2", change: "+0.00%", positive: true },
  { name: "CNY",    value: "7.24", change: "+0.12%", positive: true },
  { name: "COPPER", value: "8420", change: "-0.34%", positive: false },
];

export function SidePanel({ isOpen, countryName, onClose }: SidePanelProps) {
  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ x: "100%", opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          exit={{ x: "100%", opacity: 0 }}
          transition={{ type: "spring", damping: 30, stiffness: 300 }}
          className="absolute right-0 top-0 z-50 flex h-full w-full flex-col overflow-y-auto border-l border-border bg-background/95 p-6 shadow-2xl backdrop-blur-2xl md:w-[440px]"
        >
          <div className="mb-8 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="grid h-10 w-10 place-items-center rounded-xl border border-primary/30 bg-primary/10">
                <Crosshair size={20} className="text-primary" />
              </div>
              <div>
                <p className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground">
                  Market Analysis
                </p>
                <p className="text-xs font-bold text-primary">SELECT ASSET</p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="group rounded-xl border border-border bg-secondary/40 p-3 text-muted-foreground transition-all hover:bg-secondary active:scale-95"
              aria-label="Close panel"
            >
              <X size={20} className="transition-transform group-hover:rotate-90" />
            </button>
          </div>

          <h2 className="mb-8 text-3xl font-light tracking-tight">
            {countryName || "Global Market"}
          </h2>

          <div className="mb-8 flex gap-3 overflow-x-auto pb-2">
            {ASSETS.map((asset) => (
              <div
                key={asset.name}
                className="flex min-w-[140px] cursor-pointer flex-col gap-2 rounded-2xl border border-border bg-secondary/30 p-4 transition-all hover:border-primary/50 hover:bg-secondary/50"
              >
                <span className="font-mono text-[10px] font-bold tracking-wider text-muted-foreground">
                  {asset.name}
                </span>
                <div className="flex items-end gap-1.5">
                  <span className="text-xl font-medium">{asset.value}</span>
                  <span
                    className={cn(
                      "mb-1 text-[10px] font-bold",
                      asset.positive
                        ? "text-[hsl(var(--bull))]"
                        : "text-[hsl(var(--bear))]",
                    )}
                  >
                    {asset.change}
                  </span>
                </div>
              </div>
            ))}
          </div>

          <div className="relative flex min-h-[220px] flex-1 flex-col overflow-hidden rounded-3xl border border-border bg-card/40 p-6">
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_0%,hsl(var(--primary)/0.10),transparent_70%)]" />

            <div className="relative z-10 mb-6 flex items-center justify-between">
              <span className="font-mono text-xs font-bold uppercase tracking-widest text-muted-foreground italic">
                Price Index
              </span>
              <div className="flex items-center gap-2">
                <span className="h-1.5 w-1.5 rounded-full bg-primary animate-pulse" />
                <span className="text-[10px] font-bold text-primary">LIVE DATA</span>
              </div>
            </div>

            <div className="flex-1">
              <svg className="h-full w-full" viewBox="0 0 400 200" preserveAspectRatio="none">
                <defs>
                  <linearGradient id="lineGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="hsl(var(--primary))" stopOpacity="0.5" />
                    <stop offset="100%" stopColor="hsl(var(--primary))" stopOpacity="0" />
                  </linearGradient>
                </defs>
                <path
                  d="M 0 160 Q 50 140, 100 150 T 200 100 T 300 120 T 400 80 V 200 H 0 Z"
                  fill="url(#lineGrad)"
                />
                <path
                  d="M 0 160 Q 50 140, 100 150 T 200 100 T 300 120 T 400 80"
                  fill="none"
                  stroke="hsl(var(--primary))"
                  strokeWidth={3}
                />
              </svg>
            </div>
          </div>

          <div className="mt-8 border-t border-border pt-8">
            <div className="mb-6 flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-primary">
              <TrendingUp size={16} />
              <span>Sector Exposure</span>
            </div>
            <div className="space-y-6">
              <SectorRow name="Energy" value={35} color="bg-[hsl(var(--bull))]" />
              <SectorRow name="Defense" value={65} color="bg-[hsl(var(--bear))]" />
              <SectorRow name="Technology" value={82} color="bg-primary" />
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

function SectorRow({
  name,
  value,
  color,
}: {
  name: string;
  value: number;
  color: string;
}) {
  return (
    <div className="space-y-2">
      <div className="flex justify-between text-[11px] font-bold uppercase tracking-widest text-muted-foreground">
        <span>{name}</span>
        <span className="text-foreground">{value}%</span>
      </div>
      <div className="h-2 overflow-hidden rounded-full border border-border/50 bg-secondary p-0.5">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${value}%` }}
          transition={{ duration: 1.5, ease: "circOut" }}
          className={cn("h-full rounded-full", color)}
        />
      </div>
    </div>
  );
}
