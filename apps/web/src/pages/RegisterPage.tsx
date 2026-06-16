import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import AppNavbar from "../components/AppNavbar";
import { useAuth } from "../context/AuthContext";
import { api, INDUSTRY_SECTORS, type RegionConfig } from "../lib/api";

export default function RegisterPage() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [region, setRegion] = useState<RegionConfig | null>(null);
  const [form, setForm] = useState({
    name: "",
    email: "",
    password: "",
    organization_name: "",
    country: "UG",
    province: "CENTRAL",
    industry_sector: "Payments & Wallets",
    cipc_registration_number: "",
    vat_number: "",
    data_consent: false,
  });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const loadRegion = async (country: string) => {
    const data = await api.getRegion(country);
    setRegion(data);
    if (data.regions.length > 0 && !data.regions.some((r) => r.value === form.province)) {
      setForm((f) => ({ ...f, province: data.regions[0].value }));
    }
  };

  useEffect(() => {
    loadRegion(form.country).catch(() => {});
  }, []);

  const handleCountryChange = async (country: string) => {
    setForm((f) => ({ ...f, country }));
    try {
      await loadRegion(country);
    } catch {
      /* keep form usable */
    }
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await register(form);
      navigate("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setLoading(false);
    }
  };

  const update =
    (field: keyof typeof form) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
      if (field === "data_consent") {
        setForm((f) => ({ ...f, data_consent: (e.target as HTMLInputElement).checked }));
        return;
      }
      const value = e.target.value;
      if (field === "country") {
        void handleCountryChange(value);
        setForm((f) => ({ ...f, country: value }));
        return;
      }
      setForm((f) => ({ ...f, [field]: value }));
    };

  const labels = region?.registration;

  return (
    <div className="min-h-screen">
      <AppNavbar />
      <div className="flex items-center justify-center px-4 py-12">
        <div className="w-full max-w-lg">
          <div className="text-center mb-8">
            <p className="text-muted">Register your East African fintech organisation</p>
          </div>

          <form onSubmit={handleSubmit} className="bg-surface-raised border border-border rounded-2xl p-8 space-y-4">
            {error && (
              <div className="bg-red-500/10 border border-red-500/30 text-red-400 text-sm rounded-lg px-4 py-3">
                {error}
              </div>
            )}

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="sm:col-span-2">
                <label className="block text-sm font-medium text-muted mb-1.5">Your name</label>
                <input value={form.name} onChange={update("name")} className="input-field" required />
              </div>
              <div className="sm:col-span-2">
                <label className="block text-sm font-medium text-muted mb-1.5">Company name</label>
                <input
                  value={form.organization_name}
                  onChange={update("organization_name")}
                  className="input-field"
                  placeholder="Kampala Pay Ltd"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-muted mb-1.5">Country</label>
                <select value={form.country} onChange={update("country")} className="input-field">
                  {(region?.countries ?? [{ code: "UG", label: "Uganda" }]).map((c) => (
                    <option key={c.code} value={c.code}>
                      {c.label}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-muted mb-1.5">
                  {labels?.region_label ?? "Region"}
                </label>
                <select value={form.province} onChange={update("province")} className="input-field">
                  {(region?.regions ?? [{ value: "CENTRAL", label: "Central" }]).map((p) => (
                    <option key={p.value} value={p.value}>
                      {p.label}
                    </option>
                  ))}
                </select>
              </div>
              <div className="sm:col-span-2">
                <label className="block text-sm font-medium text-muted mb-1.5">Industry</label>
                <select value={form.industry_sector} onChange={update("industry_sector")} className="input-field">
                  {INDUSTRY_SECTORS.map((s) => (
                    <option key={s} value={s}>
                      {s}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-muted mb-1.5">
                  {labels?.company_reg_label ?? "Company registration (optional)"}
                </label>
                <input
                  value={form.cipc_registration_number}
                  onChange={update("cipc_registration_number")}
                  className="input-field"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-muted mb-1.5">
                  {labels?.vat_label ?? "Tax ID (optional)"}
                </label>
                <input value={form.vat_number} onChange={update("vat_number")} className="input-field" />
              </div>
              <div className="sm:col-span-2">
                <label className="block text-sm font-medium text-muted mb-1.5">Email</label>
                <input type="email" value={form.email} onChange={update("email")} className="input-field" required />
              </div>
              <div className="sm:col-span-2">
                <label className="block text-sm font-medium text-muted mb-1.5">Password</label>
                <input
                  type="password"
                  value={form.password}
                  onChange={update("password")}
                  minLength={8}
                  className="input-field"
                  required
                />
              </div>
            </div>

            <label className="flex items-start gap-3 text-sm text-muted cursor-pointer">
              <input
                type="checkbox"
                checked={form.data_consent}
                onChange={update("data_consent")}
                className="mt-1"
                required
              />
              <span>
                I consent to processing of personal data under{" "}
                <strong className="text-white font-medium">
                  {labels?.consent_label ?? "applicable data protection law"}
                </strong>
                .
              </span>
            </label>

            <button
              type="submit"
              disabled={loading || !form.data_consent}
              className="w-full bg-brand-600 hover:bg-brand-500 disabled:opacity-50 text-white font-medium rounded-lg py-2.5 transition-colors"
            >
              {loading ? "Creating…" : "Create organisation"}
            </button>

            <p className="text-center text-sm text-muted">
              Already registered?{" "}
              <Link to="/login" className="text-brand-400 hover:text-brand-300">
                Sign in
              </Link>
            </p>
          </form>
        </div>
      </div>
    </div>
  );
}
