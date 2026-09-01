/**
 * Shared display formatters — the single source of truth for how NexusAI
 * presents money, dates, and times to the business owner.
 *
 * Rules:
 *  - Money rounds half-up at display precision (Rs 4,850,000 → Rs 4.9M),
 *    by rounding the scaled integer rather than the float, so .x5
 *    boundaries behave like every other number in the app.
 *  - Dates render in a human format; date-only strings are parsed as LOCAL
 *    midnight so "2026-08-28" never shifts a day by timezone.
 *  - Anything unparseable falls back to the raw string — the UI never
 *    shows "Invalid Date".
 */

export function formatPKR(value: number): string {
  if (value >= 1000000) {
    return `Rs ${(Math.round(value / 100000) / 10).toFixed(1)}M`;
  }
  if (value >= 1000) return `Rs ${Math.round(value / 1000)}K`;
  return `Rs ${value}`;
}

export function formatDate(iso: string): string {
  const raw = (iso || "").trim();
  if (!raw) return "";
  // Date-only strings get a time component so they parse as local midnight
  // instead of UTC (which can display the previous day).
  const d = new Date(raw.length === 10 ? `${raw}T00:00:00` : raw);
  if (Number.isNaN(d.getTime())) return raw;
  return d.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export function formatDateTime(iso: string): string {
  const raw = (iso || "").trim();
  if (!raw) return "";
  const d = new Date(raw);
  if (Number.isNaN(d.getTime())) return raw;
  // Backend timestamps are UTC — render them UTC-labeled, never ambiguous.
  const date = d.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
    timeZone: "UTC",
  });
  return `${date} UTC`;
}
