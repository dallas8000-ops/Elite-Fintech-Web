import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import AppNavbar from "../components/AppNavbar";
import { useAuth } from "../context/AuthContext";
import { useRealtime } from "../hooks/useRealtime";
import PaymentLandscape, { SettlementBadge } from "../components/PaymentLandscape";
import SmartFeedAssistant from "../components/SmartFeedAssistant";
import {
  api,
  EVENT_LABELS,
  formatMoney,
  PAYMENT_RAIL_LABELS,
  type BillingStats,
  type PaymentEvent,
  type PaymentRailInfo,
  type SaPlan,
} from "../lib/api";

const STATUS_COLORS: Record<string, string> = {
  ACTIVE: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
  TRIALING: "bg-blue-500/20 text-blue-400 border-blue-500/30",
  PAST_DUE: "bg-amber-500/20 text-amber-400 border-amber-500/30",
  CANCELED: "bg-red-500/20 text-red-400 border-red-500/30",
  PENDING: "bg-amber-500/20 text-amber-400 border-amber-500/30",
  VERIFIED: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
};

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString("en-UG", { timeZone: "Africa/Kampala" });
}

function EventRow({ event, isNew, currency }: { event: PaymentEvent; isNew?: boolean; currency: string }) {
  const rail = event.payment_rail ? PAYMENT_RAIL_LABELS[event.payment_rail] ?? event.payment_rail : null;
  return (
    <div
      className={`flex items-center justify-between py-3 px-4 border-b border-border last:border-0 ${
        isNew ? "bg-brand-500/5" : ""
      }`}
    >
      <div className="flex items-center gap-3 min-w-0">
        <div className="w-2 h-2 rounded-full bg-emerald-400 shrink-0" />
        <div className="min-w-0">
          <p className="text-sm font-medium truncate">{EVENT_LABELS[event.type] ?? event.type}</p>
          <p className="text-xs text-muted font-mono">
            {formatDate(event.createdAt)}
            {rail && ` · ${rail}`}
            {event.payment_provider && ` · ${event.payment_provider}`}
            {event.settlementStatus && (
              <>
                {" · "}
                <SettlementBadge status={event.settlementStatus} />
              </>
            )}
          </p>
        </div>
      </div>
      <span className="text-sm font-mono text-muted shrink-0 ml-2">
        {formatMoney(event.amount, event.currency ?? currency)}
      </span>
    </div>
  );
}

export default function DashboardPage() {
  const { user, organization, role } = useAuth();
  const token = localStorage.getItem("token");
  const realtime = useRealtime(token);
  const [searchParams] = useSearchParams();

  const [stats, setStats] = useState<BillingStats | null>(null);
  const [plans, setPlans] = useState<SaPlan[]>([]);
  const [members, setMembers] = useState<{ id: string; role: string; user: { name: string; email: string } }[]>([]);
  const [loading, setLoading] = useState(true);
  const [railsData, setRailsData] = useState<{
    rails: PaymentRailInfo[];
    markets: { id: string; label: string; primary_rails: string[]; note: string }[];
    philosophy: string;
  } | null>(null);

  const [newEventIds, setNewEventIds] = useState<Set<string>>(new Set());
  const [filteredEvents, setFilteredEvents] = useState<PaymentEvent[] | null>(null);

  const checkoutStatus = searchParams.get("checkout");
  const checkoutRail = searchParams.get("rail");
  const currency =
    stats?.currency ??
    ({ KE: "kes", RW: "rwf", TZ: "tzs", UG: "ugx", ZA: "zar" }[organization?.country ?? "UG"] ?? "ugx");
  const canManage = role === "OWNER" || role === "ADMIN";

  useEffect(() => {
    async function load() {
      try {
        const [statsData, eventsData, plansData, membersData, rails] = await Promise.all([
          api.getStats(),
          api.getEvents(),
          api.getPlans(),
          api.getMembers(),
          api.getRails(),
        ]);
        setStats(statsData);
        realtime.setInitialEvents(eventsData.events);
        if (statsData.subscription) realtime.setSubscription(statsData.subscription);
        setPlans(plansData.plans);
        setMembers(membersData.members);
        setRailsData(rails);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  useEffect(() => {
    if (realtime.events.length > 0) {
      const latest = realtime.events[0];
      if (!newEventIds.has(latest.id)) {
        setNewEventIds((prev) => new Set(prev).add(latest.id));
        setTimeout(() => {
          setNewEventIds((prev) => {
            const next = new Set(prev);
            next.delete(latest.id);
            return next;
          });
        }, 3000);
      }
    }
  }, [realtime.events]);

  const subscription = realtime.subscription ?? stats?.subscription;

  const handleCheckout = async (tier: string, rail: string) => {
    const provider = rail === "CARD" ? "STRIPE" : undefined;
    const { url } = await api.checkout(tier, rail, provider);
    window.location.href = url;
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-muted">Loading dashboard…</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <AppNavbar />
      <div className="border-b border-border bg-surface-raised/40">
        <div className="max-w-7xl mx-auto px-6 py-3 flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="font-semibold">{organization?.name}</p>
            <p className="text-xs text-muted">
              {user?.email} · {role} · {organization?.country} ·{" "}
              {organization?.province?.replace(/_/g, " ")}
            </p>
          </div>
          <div className="flex items-center gap-2 text-xs">
            <span className={`w-2 h-2 rounded-full ${realtime.connected ? "bg-emerald-400" : "bg-red-400"}`} />
            <span className="text-muted">{realtime.connected ? "Live feed" : "Disconnected"}</span>
          </div>
        </div>
      </div>

      <main className="max-w-7xl mx-auto px-6 py-8 space-y-8">
        {checkoutStatus === "success" && (
          <div className="bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 rounded-xl px-5 py-4">
            Payment received
            {checkoutRail && ` via ${PAYMENT_RAIL_LABELS[checkoutRail] ?? checkoutRail}`}.
            Settlement status will update on the live feed — African EFT can take 1–3 days.
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-4 gap-5">
          <div className="bg-surface-raised border border-border rounded-xl p-6">
            <p className="text-sm text-muted mb-1">Current Plan</p>
            <p className="text-2xl font-semibold">{subscription?.planTier ?? "None"}</p>
            {subscription && (
              <span className={`inline-block mt-2 text-xs px-2.5 py-1 rounded-full border ${STATUS_COLORS[subscription.status] ?? ""}`}>
                {subscription.status}
              </span>
            )}
          </div>
          <div className="bg-surface-raised border border-border rounded-xl p-6">
            <p className="text-sm text-muted mb-1">Revenue ({currency.toUpperCase()})</p>
            <p className="text-2xl font-semibold font-mono">{formatMoney(stats?.totalRevenue ?? 0, currency)}</p>
            <p className="text-xs text-muted mt-1">VAT-inclusive · local currency</p>
          </div>
          <div className="bg-surface-raised border border-border rounded-xl p-6">
            <p className="text-sm text-muted mb-1">Payment Events</p>
            <p className="text-2xl font-semibold">{stats?.totalEvents ?? 0}</p>
          </div>
          <div className="bg-surface-raised border border-border rounded-xl p-6">
            <p className="text-sm text-muted mb-1">KYC Status</p>
            <p className="text-lg font-semibold">{organization?.fica_status ?? "PENDING"}</p>
            <p className="text-xs text-muted mt-1">Data consent recorded</p>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <section className="bg-surface-raised border border-border rounded-xl overflow-hidden">
            <div className="px-6 py-4 border-b border-border flex items-center justify-between">
              <h2 className="font-semibold">Live Payment Feed</h2>
              <span className="text-xs text-muted font-mono">MoMo · USSD · Agent cash</span>
            </div>
            <SmartFeedAssistant
              events={realtime.events}
              currency={currency}
              onFilteredChange={setFilteredEvents}
            />
            <div className="max-h-96 overflow-y-auto">
              {realtime.events.length === 0 ? (
                <p className="text-muted text-sm p-6 text-center">
                  No payment events yet. Choose a mobile money or USSD rail below.
                </p>
              ) : (filteredEvents ?? realtime.events).length === 0 ? (
                <p className="text-muted text-sm p-6 text-center">
                  No events match that search. Try a different query.
                </p>
              ) : (
                (filteredEvents ?? realtime.events).map((event) => (
                  <EventRow key={event.id} event={event} isNew={newEventIds.has(event.id)} currency={currency} />
                ))
              )}
            </div>
          </section>

          <section className="space-y-6">
            {railsData && (
              <PaymentLandscape
                rails={railsData.rails}
                markets={railsData.markets}
                philosophy={railsData.philosophy}
              />
            )}

            {canManage && (
              <div className="bg-surface-raised border border-border rounded-xl p-6">
                <h2 className="font-semibold mb-1">Subscribe by payment rail</h2>
                <p className="text-xs text-muted mb-4">
                  East Africa customers pay from their mobile wallet — not card-on-file like US SaaS.
                  {plans[0]?.fx_trading_date && (
                    <span className="block mt-1">
                      Prices updated from market rates · {plans[0].fx_trading_date}
                      {plans[0].fx_source ? ` · ${plans[0].fx_source}` : ""}
                    </span>
                  )}
                </p>
                <div className="space-y-3">
                  {plans.map((plan) => (
                    <div key={plan.tier} className="bg-surface-overlay border border-border rounded-lg p-4">
                      <div className="flex justify-between items-start mb-2">
                        <div>
                          <p className="font-medium">{plan.label}</p>
                          <p className="text-xs text-muted">{plan.description}</p>
                        </div>
                        <p className="font-mono text-brand-400">
                          {plan.amount_display ?? formatMoney(plan.amount_cents, plan.currency ?? currency)}
                        </p>
                      </div>
                      <div className="flex flex-wrap gap-2 mt-3">
                        {(plan.recommended_rails ?? []).map((rail) => (
                          <button
                            key={rail}
                            onClick={() => handleCheckout(plan.tier, rail)}
                            className="text-xs px-3 py-1.5 rounded bg-emerald-600/20 text-emerald-400 border border-emerald-500/30 hover:bg-emerald-600/30"
                          >
                            {PAYMENT_RAIL_LABELS[rail] ?? rail}
                          </button>
                        ))}
                        {(!plan.recommended_rails || plan.recommended_rails.length === 0) && (
                          <span className="text-xs text-muted">Configure Flutterwave in backend .env</span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="bg-surface-raised border border-border rounded-xl p-6">
              <h2 className="font-semibold mb-4">Compliance</h2>
              <dl className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <dt className="text-muted">Company reg</dt>
                  <dd className="font-mono">{organization?.cipc_registration_number ?? "—"}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-muted">Tax ID</dt>
                  <dd className="font-mono">{organization?.vat_number ?? "—"}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-muted">Sector</dt>
                  <dd>{organization?.industry_sector ?? "—"}</dd>
                </div>
              </dl>
            </div>

            <div className="bg-surface-raised border border-border rounded-xl p-6">
              <h2 className="font-semibold mb-4">Team ({members.length})</h2>
              <div className="space-y-3">
                {members.map((m) => (
                  <div key={m.id} className="flex items-center justify-between text-sm">
                    <div>
                      <p className="font-medium">{m.user.name}</p>
                      <p className="text-xs text-muted">{m.user.email}</p>
                    </div>
                    <span className="text-xs px-2 py-0.5 rounded bg-surface-overlay text-muted">{m.role}</span>
                  </div>
                ))}
              </div>
            </div>
          </section>
        </div>
      </main>
    </div>
  );
}
