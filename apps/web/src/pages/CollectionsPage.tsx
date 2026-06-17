import { useEffect, useState } from "react";
import AppNavbar from "../components/AppNavbar";
import { api, formatMoney, type PaymentIntent } from "../lib/api";

const STATUS_COLORS: Record<string, string> = {
  SUCCESS: "text-emerald-400 bg-emerald-500/10 border-emerald-500/30",
  PENDING: "text-amber-400 bg-amber-500/10 border-amber-500/30",
  FAILED: "text-red-400 bg-red-500/10 border-red-500/30",
  EXPIRED: "text-muted bg-surface-overlay border-border",
  CANCELLED: "text-muted bg-surface-overlay border-border",
};

export default function CollectionsPage() {
  const [intents, setIntents] = useState<PaymentIntent[]>([]);
  const [stats, setStats] = useState<{ collections_today_minor: number; pending_intents: number; failed_intents: number } | null>(null);
  const [filter, setFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const [i, s] = await Promise.all([
        api.getCollectionIntents(filter ? { status: filter } : { today: true }),
        api.getCollectionStats(),
      ]);
      setIntents(i.intents);
      setStats(s);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load collections");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [filter]);

  return (
    <div className="min-h-screen bg-surface text-white">
      <AppNavbar />
      <main className="max-w-6xl mx-auto px-6 py-8 space-y-6">
        <div>
          <h1 className="text-2xl font-semibold">Collections</h1>
          <p className="text-sm text-muted">MoMo payment intents — today&apos;s activity</p>
        </div>

        {stats && (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="bg-surface-raised border border-border rounded-xl p-4">
              <p className="text-xs text-muted">Collected today</p>
              <p className="text-xl font-mono text-emerald-400">{formatMoney(stats.collections_today_minor, "ugx")}</p>
            </div>
            <div className="bg-surface-raised border border-border rounded-xl p-4">
              <p className="text-xs text-muted">Pending</p>
              <p className="text-xl font-mono">{stats.pending_intents}</p>
            </div>
            <div className="bg-surface-raised border border-border rounded-xl p-4">
              <p className="text-xs text-muted">Failed</p>
              <p className="text-xl font-mono text-red-400">{stats.failed_intents}</p>
            </div>
          </div>
        )}

        <div className="flex gap-2 flex-wrap">
          {["", "PENDING", "SUCCESS", "FAILED"].map((s) => (
            <button
              key={s || "today"}
              type="button"
              onClick={() => setFilter(s)}
              className={`text-xs px-3 py-1.5 rounded border ${
                filter === s ? "border-emerald-500/50 text-emerald-400" : "border-border text-muted"
              }`}
            >
              {s || "Today"}
            </button>
          ))}
        </div>

        {error && <p className="text-red-400 text-sm">{error}</p>}

        <div className="space-y-3">
          {loading ? (
            <p className="text-muted text-sm">Loading…</p>
          ) : intents.length === 0 ? (
            <p className="text-muted text-sm">No collection intents for this filter.</p>
          ) : (
            intents.map((intent) => (
              <div key={intent.intentId} className="bg-surface-raised border border-border rounded-xl p-4 flex flex-wrap justify-between gap-3">
                <div>
                  <p className="font-medium">{intent.member?.fullName ?? "Member"}</p>
                  <p className="text-xs text-muted">{intent.purpose || intent.providerReference}</p>
                  <p className="text-xs font-mono text-muted mt-1">{intent.phone}</p>
                </div>
                <div className="text-right">
                  <p className="font-mono text-emerald-400">{formatMoney(intent.amountMinor, "ugx")}</p>
                  <span className={`inline-block text-xs px-2 py-0.5 rounded border mt-1 ${STATUS_COLORS[intent.status] ?? ""}`}>
                    {intent.status}
                  </span>
                </div>
              </div>
            ))
          )}
        </div>
      </main>
    </div>
  );
}
