import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

/** Merge Tailwind classes safely, resolving conflicting utility classes. */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** Format a token/dollar count for cost dashboards. */
export function formatCurrency(value: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: value < 1 ? 4 : 2,
  }).format(value);
}

export function formatNumber(value: number) {
  return new Intl.NumberFormat("en-US", { notation: "compact" }).format(value);
}

export function formatLatency(ms: number) {
  return ms < 1000 ? `${Math.round(ms)}ms` : `${(ms / 1000).toFixed(2)}s`;
}

/** "knowledge_pipeline" -> "Knowledge pipeline" */
export function humanize(value: string) {
  const s = value.replace(/[_-]+/g, " ").trim();
  return s.charAt(0).toUpperCase() + s.slice(1);
}

/** Services emit UTC timestamps, some without an offset ("2026-11-03T16:54:26"); read those as UTC, not local. */
export function parseServiceDate(value: string): Date {
  return new Date(/[zZ]|[+-]\d{2}:?\d{2}$/.test(value) ? value : `${value}Z`);
}

export function timeAgo(value: string | null | undefined) {
  if (!value) return null;
  const date = parseServiceDate(value);
  const seconds = Math.round((Date.now() - date.getTime()) / 1000);
  if (Number.isNaN(seconds)) return null;
  if (seconds < 60) return "just now";
  const units: [number, string][] = [[60, "minute"], [3600, "hour"], [86400, "day"], [2592000, "month"]];
  let [size, unit] = units[0];
  for (const u of units) if (seconds >= u[0]) [size, unit] = u;
  const n = Math.floor(seconds / size);
  return `${n} ${unit}${n === 1 ? "" : "s"} ago`;
}
