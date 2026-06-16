import { useEffect, useMemo, useState } from "react";
import { EVENT_LABELS, PAYMENT_RAIL_LABELS, formatMoney, type PaymentEvent } from "../lib/api";

/**
 * SmartFeedAssistant
 *
 * A lightweight, fully client-side "AI-ish" layer over the live billing feed:
 *  1. A natural-language search box that parses plain-English queries
 *     ("failed payments this week", "mobile money over 50000", "paid in the last 24h")
 *     into structured filters against PaymentEvent[] — no backend call, no API key.
 *  2. An auto-generated plain-English summary banner ("18 events, 2 failed,
 *     last one 3m ago via Mobile Money") so users get the gist without
 *     reading every row.
 *
 * Designed to sit directly above the existing Live Payment Feed list in
 * DashboardPage without changing how events are fetched/streamed.
 */

interface ParsedQuery {
  status?: "failed" | "succeeded" | "pending";
  rail?: string;
  minAmount?: number;
  maxAmount?: number;
  sinceMs?: number;
  raw: string;
}

const FAILED_TYPES = new Set(["PAYMENT_FAILED", "INVOICE_FAILED"]);
const SUCCESS_TYPES = new Set(["PAYMENT_SUCCEEDED", "INVOICE_PAID", "CHECKOUT_COMPLETED", "PAYSHAP_RECEIVED"]);
const PENDING_TYPES = new Set(["EFT_PENDING"]);

const RAIL_ALIASES: Record<string, string> = {
  momo: "MOBILE_MONEY",
  "mobile money": "MOBILE_MONEY",
  wallet: "MOBILE_MONEY",
  ussd: "USSD",
  card: "CARD",
  cards: "CARD",
  eft: "EFT",
  "instant eft": "INSTANT_EFT",
  payshap: "PAYSHAP",
  debit: "DEBIT_ORDER",
  "debit order": "DEBIT_ORDER",
  agent: "AGENT_CASH",
  cash: "AGENT_CASH",
  capitec: "RNCS",
};

function parseQuery(input: string): ParsedQuery {
  const q = input.toLowerCase().trim();
  const result: ParsedQuery = { raw: input };
  if (!q) return result;

  if (/\bfail(ed|ure)?\b/.test(q)) result.status = "failed";
  else if (/\bpend(ing)?\b/.test(q)) result.status = "pending";
  else if (/\b(success(ful)?|paid|succeeded|completed)\b/.test(q)) result.status = "succeeded";

  for (const [alias, rail] of Object.entries(RAIL_ALIASES)) {
    if (q.includes(alias)) {
      result.rail = rail;
      break;
    }
  }

  const over = q.match(/\b(over|above|more than|>)\s*([\d,]+)/);
  if (over) result.minAmount = Number(over[2].replace(/,/g, "")) * 100;
  const under = q.match(/\b(under|below|less than|<)\s*([\d,]+)/);
  if (under) result.maxAmount = Number(under[2].replace(/,/g, "")) * 100;

  const now = Date.now();
  if (/\btoday\b/.test(q)) result.sinceMs = now - 24 * 60 * 60 * 1000;
  else if (/\bthis week\b/.test(q)) result.sinceMs = now - 7 * 24 * 60 * 60 * 1000;
  else if (/\blast 24\s*h(ours)?\b/.test(q)) result.sinceMs = now - 24 * 60 * 60 * 1000;
  else if (/\blast hour\b/.test(q)) result.sinceMs = now - 60 * 60 * 1000;
  else {
    const hoursMatch = q.match(/\blast\s+(\d+)\s*h(ours)?\b/);
    if (hoursMatch) result.sinceMs = now - Number(hoursMatch[1]) * 60 * 60 * 1000;
    const daysMatch = q.match(/\blast\s+(\d+)\s*d(ays)?\b/);
    if (daysMatch) result.sinceMs = now - Number(daysMatch[1]) * 24 * 60 * 60 * 1000;
  }

  return result;
}

function matchesQuery(event: PaymentEvent, parsed: ParsedQuery): boolean {
  if (parsed.status === "failed" && !FAILED_TYPES.has(event.type)) return false;
  if (parsed.status === "succeeded" && !SUCCESS_TYPES.has(event.type)) return false;
  if (parsed.status === "pending" && !PENDING_TYPES.has(event.type)) return false;
  if (parsed.rail && event.payment_rail !== parsed.rail) return false;
  if (parsed.minAmount != null && (event.amount ?? 0) < parsed.minAmount) return false;
  if (parsed.maxAmount != null && (event.amount ?? 0) > parsed.maxAmount) return false;
  if (parsed.sinceMs != null && new Date(event.createdAt).getTime() < parsed.sinceMs) return false;
  return true;
}

function timeAgo(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diffMs / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

function buildSummary(events: PaymentEvent[], currency: string): string {
  if (events.length === 0) return "No payment events yet.";

  const failed = events.filter((e) => FAILED_TYPES.has(e.type)).length;
  const pending = events.filter((e) => PENDING_TYPES.has(e.type)).length;
  const succeeded = events.filter((e) => SUCCESS_TYPES.has(e.type)).length;
  const total = events
    .filter((e) => SUCCESS_TYPES.has(e.type))
    .reduce((sum, e) => sum + (e.amount ?? 0), 0);

  const parts: string[] = [`${events.length} event${events.length === 1 ? "" : "s"}`];
  if (succeeded) parts.push(`${succeeded} succeeded (${formatMoney(total, currency)})`);
  if (pending) parts.push(`${pending} pending settlement`);
  if (failed) parts.push(`${failed} failed`);

  const latest = events[0];
  const latestRail = latest.payment_rail ? PAYMENT_RAIL_LABELS[latest.payment_rail] ?? latest.payment_rail : null;
  const latestBit = `Last: ${EVENT_LABELS[latest.type] ?? latest.type}${latestRail ? ` via ${latestRail}` : ""} · ${timeAgo(latest.createdAt)}`;

  return `${parts.join(" · ")}. ${latestBit}`;
}

const SUGGESTIONS = [
  "failed payments this week",
  "mobile money over 50000",
  "pending in the last 24h",
];

interface Props {
  events: PaymentEvent[];
  currency: string;
  onFilteredChange: (filtered: PaymentEvent[] | null) => void;
}

export default function SmartFeedAssistant({ events, currency, onFilteredChange }: Props) {
  const [query, setQuery] = useState("");

  const summary = useMemo(() => buildSummary(events, currency), [events, currency]);

  const filtered = useMemo(() => {
    if (!query.trim()) return null;
    const parsed = parseQuery(query);
    return events.filter((e) => matchesQuery(e, parsed));
  }, [events, query]);

  useEffect(() => {
    onFilteredChange(filtered);
  }, [filtered, onFilteredChange]);

  const handleChange = (value: string) => {
    setQuery(value);
  };

  return (
    <div className="border-b border-border bg-surface-overlay/40">
      <div className="px-4 py-3 space-y-2">
        <p className="text-xs text-muted leading-relaxed">{summary}</p>
        <div className="relative">
          <input
            value={query}
            onChange={(e) => handleChange(e.target.value)}
            placeholder="Ask the feed… e.g. failed payments this week"
            className="w-full bg-surface border border-border rounded-lg pl-3 pr-8 py-2 text-sm text-white placeholder:text-muted focus:outline-none focus:ring-2 focus:ring-brand-500/50 focus:border-brand-500"
          />
          {query && (
            <button
              onClick={() => handleChange("")}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-muted hover:text-white text-xs"
              aria-label="Clear search"
            >
              ✕
            </button>
          )}
        </div>
        {!query && (
          <div className="flex flex-wrap gap-1.5">
            {SUGGESTIONS.map((s) => (
              <button
                key={s}
                onClick={() => handleChange(s)}
                className="text-[11px] px-2 py-1 rounded-full bg-surface-raised border border-border text-muted hover:text-white hover:border-brand-500/50"
              >
                {s}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
