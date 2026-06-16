import { EVENT_LABELS, PAYMENT_RAIL_LABELS, type PaymentRailInfo } from "../lib/api";

const SETTLEMENT_COLORS: Record<string, string> = {
  SETTLED: "text-emerald-400",
  PENDING: "text-amber-400",
  PROCESSING: "text-blue-400",
  FAILED: "text-red-400",
};

interface Props {
  rails: PaymentRailInfo[];
  markets: { id: string; label: string; primary_rails: string[]; note: string }[];
  philosophy?: string;
}

export default function PaymentLandscape({ rails, markets, philosophy }: Props) {
  const za = markets.find((m) => m.id === "ZA");
  const us = markets.find((m) => m.id === "US_EU");

  return (
    <div className="bg-surface-raised border border-border rounded-xl p-6 space-y-5">
      <div>
        <h2 className="font-semibold">African vs Western Payments</h2>
        <p className="text-xs text-muted mt-1 leading-relaxed">
          {philosophy ??
            "Africa routes money by bank account, wallet, and mandate — not card-on-file alone."}
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
        <div className="bg-surface-overlay rounded-lg p-4 border border-emerald-500/20">
          <p className="text-emerald-400 font-medium text-xs mb-2">{za?.label ?? "South Africa"}</p>
          <p className="text-xs text-muted mb-2">{za?.note}</p>
          <div className="flex flex-wrap gap-1">
            {za?.primary_rails.map((r) => (
              <span key={r} className="text-[10px] px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-300">
                {PAYMENT_RAIL_LABELS[r] ?? r}
              </span>
            ))}
          </div>
        </div>
        <div className="bg-surface-overlay rounded-lg p-4 border border-border">
          <p className="text-muted font-medium text-xs mb-2">{us?.label ?? "USA / Europe"}</p>
          <p className="text-xs text-muted mb-2">{us?.note}</p>
          <div className="flex flex-wrap gap-1">
            {us?.primary_rails.map((r) => (
              <span key={r} className="text-[10px] px-2 py-0.5 rounded bg-surface-raised text-muted">
                {r}
              </span>
            ))}
          </div>
        </div>
      </div>

      <div>
        <p className="text-xs font-medium text-muted mb-2">SA checkout rails</p>
        <div className="space-y-2">
          {rails.slice(0, 5).map((rail) => (
            <div key={rail.id} className="flex justify-between items-start text-xs gap-2">
              <div>
                <span className="font-medium">{rail.label}</span>
                {rail.is_async && (
                  <span className="ml-2 text-amber-400/80">async settlement</span>
                )}
                <p className="text-muted mt-0.5">{rail.settlement}</p>
              </div>
              <span className={rail.available ? "text-emerald-400" : "text-muted"}>
                {rail.available ? "ready" : "configure PSP"}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export function SettlementBadge({ status }: { status?: string }) {
  if (!status) return null;
  return (
    <span className={`text-[10px] font-mono ${SETTLEMENT_COLORS[status] ?? "text-muted"}`}>
      {status}
    </span>
  );
}

export { EVENT_LABELS };
