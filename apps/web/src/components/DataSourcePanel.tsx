import { useState } from "react";

interface SourceRow {
  section: string;
  api?: string;
  storage: string;
  editable: string;
}

const SOURCES: SourceRow[] = [
  {
    section: "Current plan & subscription",
    api: "GET /api/v1/billing/stats/",
    storage: "billing.Subscription (DB)",
    editable: "Checkout flow · Django admin",
  },
  {
    section: "Revenue & event counts",
    api: "GET /api/v1/billing/stats/",
    storage: "Aggregated from billing.PaymentEvent",
    editable: "Django admin (events)",
  },
  {
    section: "KYC status",
    api: "GET /api/v1/auth/me/",
    storage: "organizations.Organization.fica_status",
    editable: "Django admin only",
  },
  {
    section: "Live payment feed",
    api: "GET /api/v1/billing/events/ + WebSocket /ws/billing/",
    storage: "billing.PaymentEvent · seed: seed_demo.py",
    editable: "Django admin · re-run npm run seed",
  },
  {
    section: "Feed search & summary",
    storage: "Client-side only (SmartFeedAssistant.tsx)",
    editable: "Filters in browser — no API",
  },
  {
    section: "Payment rails landscape",
    api: "GET /api/v1/billing/rails/",
    storage: "billing/views.py (hardcoded)",
    editable: "Backend source code",
  },
  {
    section: "Subscribe plans",
    api: "GET /api/v1/billing/plans/",
    storage: "billing/services/east_africa_constants.py",
    editable: "Backend source code",
  },
  {
    section: "Compliance (company reg, tax, sector)",
    api: "GET /api/v1/auth/me/ · PATCH /api/v1/org/",
    storage: "organizations.Organization (DB)",
    editable: "Settings page · Django admin",
  },
  {
    section: "Team members",
    api: "GET /api/v1/org/members/",
    storage: "organizations.Membership (DB)",
    editable: "Django admin · invite API (no UI yet)",
  },
];

export default function DataSourcePanel() {
  const [open, setOpen] = useState(false);

  return (
    <section className="bg-surface-raised border border-border rounded-xl overflow-hidden">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full px-6 py-4 flex items-center justify-between text-left hover:bg-surface-overlay/40 transition-colors"
      >
        <div>
          <h2 className="font-semibold text-sm">Where does this data come from?</h2>
          <p className="text-xs text-muted mt-0.5">
            API endpoints, database tables, and what you can edit
          </p>
        </div>
        <span className="text-muted text-sm shrink-0 ml-4">{open ? "▾" : "▸"}</span>
      </button>

      {open && (
        <div className="border-t border-border overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="text-muted border-b border-border bg-surface-overlay/30">
                <th className="text-left font-medium px-4 py-2">Dashboard section</th>
                <th className="text-left font-medium px-4 py-2">API</th>
                <th className="text-left font-medium px-4 py-2">Source</th>
                <th className="text-left font-medium px-4 py-2">How to edit</th>
              </tr>
            </thead>
            <tbody>
              {SOURCES.map((row) => (
                <tr key={row.section} className="border-b border-border/60 last:border-0">
                  <td className="px-4 py-2.5 font-medium whitespace-nowrap">{row.section}</td>
                  <td className="px-4 py-2.5 font-mono text-muted">{row.api ?? "—"}</td>
                  <td className="px-4 py-2.5 text-muted">{row.storage}</td>
                  <td className="px-4 py-2.5 text-brand-400/90">{row.editable}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="px-4 py-3 text-[11px] text-muted border-t border-border">
            Demo events are seeded by{" "}
            <code className="text-white/70">apps/backend/accounts/management/commands/seed_demo.py</code>
            . Run <code className="text-white/70">npm run seed</code> to reset demo data.
          </p>
        </div>
      )}
    </section>
  );
}
