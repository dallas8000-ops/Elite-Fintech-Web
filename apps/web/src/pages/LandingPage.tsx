import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import AppNavbar from "../components/AppNavbar";
import { api, type PlatformCapabilities, type ReadinessReport, type RegionConfig } from "../lib/api";

export default function LandingPage() {
  const [caps, setCaps] = useState<PlatformCapabilities | null>(null);
  const [region, setRegion] = useState<RegionConfig | null>(null);
  const [readiness, setReadiness] = useState<ReadinessReport | null>(null);

  useEffect(() => {
    api.getCapabilities().then(setCaps).catch(() => {});
    api.getRegion().then(setRegion).catch(() => {});
    api.getReadiness().then(setReadiness).catch(() => {});
  }, []);

  return (
    <div className="min-h-screen">
      <AppNavbar />

      <section className="max-w-6xl mx-auto px-6 py-20 text-center">
        <p className="text-emerald-400 text-sm font-medium mb-4 tracking-wide uppercase">
          {caps?.tier ?? "ENTERPRISE"} · East Africa Fintech Infrastructure
          {readiness != null && (
            <span className="ml-2 text-white/50">
              · readiness {readiness.score}/100
            </span>
          )}
        </p>
        <h1 className="text-4xl md:text-5xl font-bold tracking-tight max-w-3xl mx-auto leading-tight">
          Billing built for mobile money — Uganda, Kenya, Rwanda, Tanzania
        </h1>
        <p className="text-muted text-lg mt-6 max-w-2xl mx-auto leading-relaxed">
          Multi-tenant billing in local currency (UGX, KES, RWF, TZS). MTN MoMo, M-Pesa, USSD, and
          Flutterwave rails — not US card SaaS. Real-time ops, domain white-label, AI setup APIs.
        </p>
        <div className="flex flex-wrap justify-center gap-4 mt-10">
          <Link
            to="/demo"
            className="bg-emerald-600 hover:bg-emerald-500 px-8 py-3 rounded-xl font-medium transition-colors"
          >
            Try live demo
          </Link>
          <Link
            to="/register"
            className="bg-brand-600 hover:bg-brand-500 px-8 py-3 rounded-xl font-medium transition-colors"
          >
            Launch your organisation
          </Link>
          <a
            href="/api/v1/platform/capabilities/"
            target="_blank"
            rel="noreferrer"
            className="border border-border hover:border-brand-500/50 px-8 py-3 rounded-xl font-medium text-muted hover:text-white transition-colors"
          >
            View API capabilities
          </a>
        </div>
      </section>

      <section className="max-w-6xl mx-auto px-6 pb-16 grid grid-cols-1 md:grid-cols-3 gap-6">
        {[
          {
            title: "Mobile money first",
            body: "MTN MoMo, M-Pesa, Airtel Money, USSD — not card-on-file by default.",
          },
          {
            title: "East Africa compliance",
            body: "Data protection laws, local VAT (URA, KRA, RRA, TRA), central bank PSP rules.",
          },
          {
            title: "AI automation setup",
            body: "Setup Transfer API links your domain, outputs DNS + env manifest for Cursor/CI.",
          },
        ].map((f) => (
          <div key={f.title} className="bg-surface-raised border border-border rounded-xl p-6 text-left">
            <h3 className="font-semibold mb-2">{f.title}</h3>
            <p className="text-sm text-muted leading-relaxed">{f.body}</p>
          </div>
        ))}
      </section>

      {caps?.next_tier === "PLATINUM" && (
        <section className="border-t border-border bg-gradient-to-b from-violet-500/5 to-transparent py-16">
          <div className="max-w-6xl mx-auto px-6">
            <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-8">
              <div className="max-w-xl">
                <p className="text-violet-400 text-xs font-medium uppercase tracking-widest mb-2">
                  Higher tier · {caps.next_tier}
                </p>
                <h2 className="text-2xl font-semibold mb-3">
                  Institutional-grade when you outgrow standard enterprise
                </h2>
                <p className="text-sm text-muted leading-relaxed">
                  PLATINUM adds dedicated tenancy, multi-region DR, immutable audit export, central bank
                  reporting hooks, and 99.9% SLA monitoring — for banks, telcos, and licensed PSPs.
                </p>
                {readiness && readiness.score < 95 && (
                  <p className="text-xs text-muted mt-4">
                    Deployment readiness is {readiness.score}/100 — close the gaps below to unlock{" "}
                    {readiness.deployment_tier === "ENTERPRISE" ? "PLATINUM" : readiness.next_tier ?? "PLATINUM"}.
                  </p>
                )}
              </div>
              <div className="flex-1 grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
                {(caps.upgrade_capabilities ?? []).slice(0, 6).map((cap) => (
                  <div
                    key={cap.id}
                    className="bg-surface-overlay border border-violet-500/20 rounded-lg px-4 py-3"
                  >
                    <p className="font-medium text-white/90">{cap.label}</p>
                    {cap.note && <p className="text-xs text-muted mt-1">{cap.note}</p>}
                  </div>
                ))}
              </div>
            </div>
            {(readiness?.gaps?.length ?? caps.upgrade_hints?.length) ? (
              <div className="mt-8 bg-surface-raised border border-border rounded-xl p-5">
                <p className="text-xs uppercase tracking-widest text-muted mb-3">Upgrade path</p>
                <ul className="space-y-2 text-sm text-muted">
                  {(readiness?.gaps ?? []).slice(0, 3).map((gap) => (
                    <li key={gap.id} className="flex gap-2">
                      <span className="text-amber-400 shrink-0">→</span>
                      {gap.fix}
                    </li>
                  ))}
                  {(caps.upgrade_hints ?? []).slice(0, 2).map((hint) => (
                    <li key={hint} className="flex gap-2">
                      <span className="text-emerald-400 shrink-0">→</span>
                      {hint}
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
          </div>
        </section>
      )}

      {region && (
        <section className="border-t border-border bg-surface-raised/50 py-16">
          <div className="max-w-6xl mx-auto px-6">
            <h2 className="text-xl font-semibold text-center mb-2">Pricing by country</h2>
          <p className="text-center text-sm text-muted mb-10 max-w-xl mx-auto">
            Fixed USD anchors converted daily to UGX, KES, RWF, TZS using live market rates.
            {region.pricing?.trading_date && (
              <span className="block mt-1 text-xs">
                Last market update: {region.pricing.trading_date} · {region.pricing.source}
              </span>
            )}
          </p>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {region.countries.map((c) => (
                <div key={c.code} className="bg-surface-overlay border border-border rounded-xl p-5">
                  <p className="font-semibold text-emerald-400 mb-3">{c.label}</p>
                  <div className="space-y-2 text-sm">
                    {c.plans.map((plan) => (
                      <div key={plan.tier} className="flex justify-between gap-2">
                        <span className="text-muted">{plan.label}</span>
                        <span className="font-mono text-white shrink-0">
                          {plan.amount_display ?? plan.amount_cents}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>
      )}

      <section className="border-t border-border py-16 bg-surface-raised/30">
        <div className="max-w-6xl mx-auto px-6">
          <h2 className="text-xl font-semibold text-center mb-2">Tier positioning</h2>
          <p className="text-center text-sm text-muted mb-2 max-w-2xl mx-auto">
            Not a basic Stripe widget — built for East Africa mobile money. Prices track daily market
            FX
            {region?.pricing?.trading_date ? ` · updated ${region.pricing.trading_date}` : ""}.
          </p>
          {region?.default_country && (
            <p className="text-center text-xs text-muted mb-10">
              Shown in {region.countries.find((c) => c.code === region.default_country)?.label ?? "Uganda"}{" "}
              — see all countries above
            </p>
          )}

          <div className="grid grid-cols-1 md:grid-cols-3 gap-5 text-sm">
            {(
              [
                {
                  tier: "STARTER" as const,
                  tagline: "Starter",
                  body: "Early-stage fintechs, SACCOs, and agent networks.",
                  features: ["500 MoMo txns/mo", "MTN & M-Pesa reconciliation", "Data protection audit log"],
                  highlight: false,
                },
                {
                  tier: "PRO" as const,
                  tagline: "Pro",
                  body: "Growing wallets and payment platforms — no custom domain yet.",
                  features: ["Unlimited MoMo + USSD webhooks", "Flutterwave / Pesapal", "KYC + VAT reporting"],
                  highlight: false,
                },
                {
                  tier: "ENTERPRISE" as const,
                  tagline: "Enterprise",
                  body: "This platform — banks, telcos, and licensed PSPs.",
                  features: ["MoMo · USSD · agent rails", "Custom domain white-label", "AI automation setup API"],
                  highlight: true,
                },
              ] as const
            ).map((card) => {
              const defaultPlans =
                region?.countries.find((c) => c.code === region.default_country)?.plans ??
                region?.countries[0]?.plans;
              const plan = defaultPlans?.find((p) => p.tier === card.tier);
              const usd = region?.usd_anchors?.[card.tier];

              return (
                <div
                  key={card.tier}
                  className={`rounded-xl p-6 border flex flex-col ${
                    card.highlight
                      ? "border-emerald-500/50 bg-emerald-500/5 shadow-lg shadow-emerald-500/5"
                      : "border-border bg-surface-overlay"
                  }`}
                >
                  <p className="text-[10px] uppercase tracking-widest text-emerald-400/80 mb-1">
                    {card.highlight ? "This platform" : card.tier}
                  </p>
                  <p className="text-lg font-semibold mb-3">{card.tagline}</p>

                  {plan ? (
                    <div className="mb-4">
                      <p className="text-2xl font-bold font-mono text-white">
                        {plan.amount_display ?? plan.amount_cents}
                        <span className="text-sm font-normal text-muted"> /mo</span>
                      </p>
                      {usd != null && (
                        <p className="text-xs text-muted mt-1">≈ ${usd} USD anchor · VAT inclusive</p>
                      )}
                    </div>
                  ) : (
                    <p className="text-muted text-sm mb-4 font-mono">Loading market price…</p>
                  )}

                  <p className="text-muted text-xs leading-relaxed mb-4">{card.body}</p>

                  <ul className="space-y-2 text-xs text-muted flex-1 mb-6">
                    {card.features.map((f) => (
                      <li key={f} className="flex items-start gap-2">
                        <span
                          className={`mt-1 w-1.5 h-1.5 rounded-full shrink-0 ${
                            card.highlight ? "bg-emerald-400" : "bg-brand-500/60"
                          }`}
                        />
                        {f}
                      </li>
                    ))}
                  </ul>

                  <Link
                    to="/register"
                    className={`block text-center py-2.5 rounded-lg font-medium transition-colors ${
                      card.highlight
                        ? "bg-brand-600 hover:bg-brand-500 text-white"
                        : "border border-border hover:border-brand-500/50 text-muted hover:text-white"
                    }`}
                  >
                    Get started
                  </Link>
                </div>
              );
            })}
          </div>

          <p className="text-center text-xs text-muted mt-8 max-w-lg mx-auto">
            <span className="text-white/70">Basic tier</span> (typical US card widgets ~$9–29/mo) lacks
            mobile money, USSD, and East Africa compliance — not what this region needs.
          </p>
        </div>
      </section>

      <footer className="border-t border-border py-8 text-center text-xs text-muted">
        Elite Fintech Systems · Django + React · East Africa · {caps?.tier ?? "ENTERPRISE"} tier
        {readiness != null ? ` · deployment ${readiness.deployment_tier} (${readiness.score}/100)` : ""}
      </footer>
    </div>
  );
}
