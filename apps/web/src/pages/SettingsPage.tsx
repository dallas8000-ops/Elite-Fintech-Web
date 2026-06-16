import { useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import AppNavbar from "../components/AppNavbar";
import { useAuth } from "../context/AuthContext";
import { api, getAdminUrl, INDUSTRY_SECTORS, type RegionConfig } from "../lib/api";

export default function SettingsPage() {
  const { organization, role, updateOrganization } = useAuth();
  const canManage = role === "OWNER" || role === "ADMIN";

  const [region, setRegion] = useState<RegionConfig | null>(null);
  const [form, setForm] = useState({
    name: "",
    province: "",
    industry_sector: "",
    cipc_registration_number: "",
    vat_number: "",
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    async function load() {
      try {
        const country = organization?.country ?? "UG";
        const [regionData, orgData] = await Promise.all([
          api.getRegion(country),
          api.getOrganization(),
        ]);
        setRegion(regionData);
        const org = orgData.organization;
        setForm({
          name: org.name ?? "",
          province: org.province ?? "",
          industry_sector: org.industry_sector ?? "",
          cipc_registration_number: org.cipc_registration_number ?? "",
          vat_number: org.vat_number ?? "",
        });
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load settings");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [organization?.country]);

  const update =
    (field: keyof typeof form) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
      setForm((f) => ({ ...f, [field]: e.target.value }));
      setSaved(false);
    };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!canManage) return;
    setSaving(true);
    setError("");
    setSaved(false);
    try {
      await updateOrganization({
        name: form.name,
        province: form.province,
        industry_sector: form.industry_sector,
        cipc_registration_number: form.cipc_registration_number || undefined,
        vat_number: form.vat_number || undefined,
      });
      setSaved(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  };

  const labels = region?.registration;

  if (loading) {
    return (
      <div className="min-h-screen">
        <AppNavbar />
        <div className="flex items-center justify-center py-24 text-muted">Loading settings…</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <AppNavbar />
      <main className="max-w-2xl mx-auto px-6 py-8 space-y-6">
        <div>
          <h1 className="text-xl font-semibold">Organisation settings</h1>
          <p className="text-sm text-muted mt-1">
            Compliance and profile fields shown on your dashboard. KYC status is managed by admins.
          </p>
        </div>

        {!canManage && (
          <div className="bg-amber-500/10 border border-amber-500/30 text-amber-300 text-sm rounded-lg px-4 py-3">
            You have read-only access. Ask an owner or admin to update these fields.
          </div>
        )}

        <form onSubmit={handleSubmit} className="bg-surface-raised border border-border rounded-2xl p-8 space-y-4">
          {error && (
            <div className="bg-red-500/10 border border-red-500/30 text-red-400 text-sm rounded-lg px-4 py-3">
              {error}
            </div>
          )}
          {saved && (
            <div className="bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-sm rounded-lg px-4 py-3">
              Settings saved. Changes appear on the dashboard immediately.
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-muted mb-1.5">Company name</label>
            <input
              value={form.name}
              onChange={update("name")}
              className="input-field"
              disabled={!canManage}
              required
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-muted mb-1.5">Country</label>
              <input
                value={organization?.country ?? "UG"}
                className="input-field opacity-60"
                disabled
                readOnly
              />
              <p className="text-[11px] text-muted mt-1">Contact support to change market country.</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-muted mb-1.5">Region</label>
              <select
                value={form.province}
                onChange={update("province")}
                className="input-field"
                disabled={!canManage}
              >
                {(region?.regions ?? []).map((r) => (
                  <option key={r.value} value={r.value}>
                    {r.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-muted mb-1.5">Industry sector</label>
            <select
              value={form.industry_sector}
              onChange={update("industry_sector")}
              className="input-field"
              disabled={!canManage}
            >
              {INDUSTRY_SECTORS.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-muted mb-1.5">
              {labels?.company_reg_label ?? "Company registration"}
            </label>
            <input
              value={form.cipc_registration_number}
              onChange={update("cipc_registration_number")}
              className="input-field font-mono"
              disabled={!canManage}
              placeholder="Optional"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-muted mb-1.5">
              {labels?.vat_label ?? "Tax ID"}
            </label>
            <input
              value={form.vat_number}
              onChange={update("vat_number")}
              className="input-field font-mono"
              disabled={!canManage}
              placeholder="Optional"
            />
          </div>

          <div className="flex flex-wrap items-center gap-3 pt-2">
            {canManage && (
              <button
                type="submit"
                disabled={saving}
                className="bg-brand-600 hover:bg-brand-500 disabled:opacity-50 text-white font-medium rounded-lg px-5 py-2.5 transition-colors"
              >
                {saving ? "Saving…" : "Save changes"}
              </button>
            )}
            <Link to="/dashboard" className="text-sm text-muted hover:text-white transition-colors">
              Back to dashboard
            </Link>
          </div>
        </form>

        {canManage && (
          <div className="bg-surface-raised border border-border rounded-xl p-6">
            <h2 className="font-semibold text-sm mb-1">Power-user tools</h2>
            <p className="text-xs text-muted mb-3">
              Edit payment events, subscriptions, and KYC status directly in the database via Django admin.
            </p>
            <a
              href={getAdminUrl()}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-brand-400 hover:text-brand-300"
            >
              Open Django admin ↗
            </a>
          </div>
        )}
      </main>
    </div>
  );
}
