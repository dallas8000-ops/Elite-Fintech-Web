import { useEffect, useState, type FormEvent } from "react";
import AppNavbar from "../components/AppNavbar";
import { api, type SetupManifest } from "../lib/api";

export default function SetupPage() {
  const [manifest, setManifest] = useState<SetupManifest | null>(null);
  const [domain, setDomain] = useState("");
  const [loading, setLoading] = useState(true);
  const [applying, setApplying] = useState(false);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState("");

  const load = async () => {
    try {
      const data = await api.getSetup();
      setManifest(data);
      if (data.target_domain) setDomain(data.target_domain);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load setup");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const handleApply = async (e: FormEvent) => {
    e.preventDefault();
    setApplying(true);
    setError("");
    try {
      const data = await api.applySetup({
        target_domain: domain,
        automation_agent: "cursor",
      });
      setManifest(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Setup failed");
    } finally {
      setApplying(false);
    }
  };

  const copy = (text: string, key: string) => {
    navigator.clipboard.writeText(text);
    setCopied(key);
    setTimeout(() => setCopied(""), 2000);
  };

  if (loading) {
    return (
      <div className="min-h-screen">
        <AppNavbar />
        <div className="flex items-center justify-center py-24 text-muted">Loading setup…</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <AppNavbar />
      <div className="border-b border-border bg-surface-raised/40">
        <div className="max-w-4xl mx-auto px-6 py-3">
          <h1 className="font-semibold">Domain & automation setup</h1>
          <p className="text-xs text-muted">ENTERPRISE · AI-ready setup transfer</p>
        </div>
      </div>

      <main className="max-w-4xl mx-auto px-6 py-8 space-y-8">
        <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-xl p-5 text-sm text-emerald-300">
          Link <strong className="text-white">api.yourdomain.com</strong> and{" "}
          <strong className="text-white">app.yourdomain.com</strong> to this platform.
          The Setup Transfer API returns DNS records and environment variables for Cursor, GitHub Actions, or Terraform.
        </div>

        {error && (
          <div className="bg-red-500/10 border border-red-500/30 text-red-400 rounded-lg px-4 py-3 text-sm">
            {error}
          </div>
        )}

        <form onSubmit={handleApply} className="bg-surface-raised border border-border rounded-xl p-6 space-y-4">
          <h2 className="font-semibold">1. Link your domain</h2>
          <div>
            <label className="block text-sm text-muted mb-1">Base domain</label>
            <input
              value={domain}
              onChange={(e) => setDomain(e.target.value)}
              placeholder="ubuntu-pay.co.za"
              className="input-field"
              required
            />
          </div>
          <button
            type="submit"
            disabled={applying}
            className="bg-brand-600 hover:bg-brand-500 disabled:opacity-50 px-6 py-2.5 rounded-lg font-medium"
          >
            {applying ? "Generating manifest…" : "Apply setup transfer"}
          </button>
          {manifest?.transfer_token && (
            <p className="text-xs text-muted font-mono break-all">
              Transfer token: {manifest.transfer_token}
            </p>
          )}
        </form>

        {manifest && (
          <>
            <section className="bg-surface-raised border border-border rounded-xl p-6">
              <h2 className="font-semibold mb-4">2. Setup progress</h2>
              <ul className="space-y-2">
                {manifest.setup_steps.map((step) => (
                  <li key={step.id} className="flex items-center gap-3 text-sm">
                    <span
                      className={`w-5 h-5 rounded-full flex items-center justify-center text-xs ${
                        step.done ? "bg-emerald-500/20 text-emerald-400" : "bg-surface-overlay text-muted"
                      }`}
                    >
                      {step.done ? "✓" : "·"}
                    </span>
                    {step.label}
                  </li>
                ))}
              </ul>
            </section>

            <section className="bg-surface-raised border border-border rounded-xl p-6">
              <h2 className="font-semibold mb-4">3. Production URLs</h2>
              <dl className="space-y-2 text-sm font-mono">
                {Object.entries(manifest.urls).map(([k, v]) => (
                  <div key={k} className="flex justify-between gap-4">
                    <dt className="text-muted shrink-0">{k}</dt>
                    <dd className="text-right break-all">{v}</dd>
                  </div>
                ))}
              </dl>
            </section>

            <section className="bg-surface-raised border border-border rounded-xl p-6">
              <h2 className="font-semibold mb-4">4. DNS records (add at your registrar)</h2>
              {["api", "app"].map((kind) => (
                <div key={kind} className="mb-4">
                  <p className="text-xs text-muted uppercase mb-2">{kind}</p>
                  {(manifest.dns_records[kind] ?? []).length === 0 ? (
                    <p className="text-sm text-muted">Apply setup transfer first to generate records.</p>
                  ) : (
                    <pre className="text-xs bg-surface-overlay p-4 rounded-lg overflow-x-auto">
                      {JSON.stringify(manifest.dns_records[kind], null, 2)}
                    </pre>
                  )}
                </div>
              ))}
            </section>

            <section className="bg-surface-raised border border-border rounded-xl p-6">
              <h2 className="font-semibold mb-4">5. Environment (deploy / AI automation)</h2>
              <pre className="text-xs bg-surface-overlay p-4 rounded-lg overflow-x-auto">
                {Object.entries(manifest.environment)
                  .map(([k, v]) => `${k}=${v}`)
                  .join("\n")}
              </pre>
              <button
                type="button"
                onClick={() =>
                  copy(
                    Object.entries(manifest.environment)
                      .map(([k, v]) => `${k}=${v}`)
                      .join("\n"),
                    "env"
                  )
                }
                className="mt-3 text-xs text-brand-400 hover:text-brand-300"
              >
                {copied === "env" ? "Copied!" : "Copy .env block"}
              </button>
            </section>

            <section className="bg-surface-raised border border-border rounded-xl p-6">
              <h2 className="font-semibold mb-4">6. Webhook URLs (register at PayFast / Stripe)</h2>
              <dl className="space-y-2 text-sm font-mono">
                {Object.entries(manifest.webhook_urls).map(([k, v]) => (
                  <div key={k} className="flex justify-between gap-4 items-start">
                    <dt className="text-muted">{k}</dt>
                    <dd className="text-right break-all text-xs">{v}</dd>
                  </div>
                ))}
              </dl>
            </section>

            <section className="bg-surface-raised border border-border rounded-xl p-6 text-sm text-muted">
              <h2 className="font-semibold text-white mb-2">AI automation</h2>
              <p className="mb-2">{manifest.automation.instructions ?? "Use apply_endpoint with your transfer_token."}</p>
              <p className="font-mono text-xs break-all text-brand-400">{manifest.automation.apply_endpoint}</p>
            </section>
          </>
        )}
      </main>
    </div>
  );
}
