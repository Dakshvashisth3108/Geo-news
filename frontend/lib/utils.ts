import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/** shadcn classic — merges Tailwind classes with conflict resolution. */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** Compact relative-time formatter (e.g. "3m ago", "2h ago"). */
export function timeAgo(input: string | Date): string {
  const date = typeof input === "string" ? new Date(input) : input;
  const seconds = Math.max(1, Math.floor((Date.now() - date.getTime()) / 1000));

  const units: Array<[Intl.RelativeTimeFormatUnit, number]> = [
    ["year", 60 * 60 * 24 * 365],
    ["month", 60 * 60 * 24 * 30],
    ["day", 60 * 60 * 24],
    ["hour", 60 * 60],
    ["minute", 60],
    ["second", 1],
  ];

  for (const [unit, secsInUnit] of units) {
    if (seconds >= secsInUnit) {
      const value = Math.floor(seconds / secsInUnit);
      return new Intl.RelativeTimeFormat("en", { style: "narrow" }).format(
        -value,
        unit,
      );
    }
  }
  return "just now";
}

/** Clamp helper — keeps confidence/uncertainty bars from overflowing. */
export function clamp(value: number, min = 0, max = 1): number {
  return Math.min(Math.max(value, min), max);
}
