import { useCallback, useEffect, useState } from "react";
import AppNavbar from "../components/AppNavbar";
import { useAuth } from "../context/AuthContext";
import { api, formatMoney, type SaccoMember, type CollectionProduct } from "../lib/api";

export default function MembersPage() {
  const { role } = useAuth();
  const canManage = role === "OWNER" || role === "ADMIN";
  const [members, setMembers] = useState<SaccoMember[]>([]);
  const [products, setProducts] = useState<CollectionProduct[]>([]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showAdd, setShowAdd] = useState(false);
  const [collectMember, setCollectMember] = useState<SaccoMember | null>(null);
  const [collectResult, setCollectResult] = useState<{ message: string; intentId?: string } | null>(null);
  const [form, setForm] = useState({ member_number: "", full_name: "", phone: "", momo_network: "MTN" });

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [m, p] = await Promise.all([api.getSaccoMembers(query || undefined), api.getCollectionProducts()]);
      setMembers(m.members);
      setProducts(p.products);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load members");
    } finally {
      setLoading(false);
    }
  }, [query]);

  useEffect(() => {
    load();
  }, [load]);

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.createSaccoMember(form);
      setShowAdd(false);
      setForm({ member_number: "", full_name: "", phone: "", momo_network: "MTN" });
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to add member");
    }
  };

  const handleCollect = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!collectMember) return;
    const fd = new FormData(e.currentTarget);
    const productId = fd.get("product_id") as string;
    const amount = fd.get("amount_minor") as string;
    const purpose = fd.get("purpose") as string;
    try {
      const result = await api.initiateCollection({
        member_id: collectMember.id,
        product_id: productId || undefined,
        amount_minor: amount ? Number(amount) : undefined,
        purpose: purpose || undefined,
      });
      setCollectResult({ message: result.message, intentId: result.intent_id });
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Collection failed");
    }
  };

  return (
    <div className="min-h-screen bg-surface text-white">
      <AppNavbar />
      <main className="max-w-6xl mx-auto px-6 py-8 space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold">SACCO Members</h1>
            <p className="text-sm text-muted">Urban SACCO registry — Uganda MoMo collections</p>
          </div>
          {canManage && (
            <button
              type="button"
              onClick={() => setShowAdd(true)}
              className="bg-emerald-600 hover:bg-emerald-500 px-4 py-2 rounded-lg text-sm font-medium"
            >
              Add member
            </button>
          )}
        </div>

        {error && <p className="text-red-400 text-sm">{error}</p>}

        <input
          type="search"
          placeholder="Search name, member #, phone…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="w-full max-w-md bg-surface-overlay border border-border rounded-lg px-4 py-2 text-sm"
        />

        <div className="bg-surface-raised border border-border rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead className="text-muted border-b border-border">
              <tr>
                <th className="text-left p-4">Member #</th>
                <th className="text-left p-4">Name</th>
                <th className="text-left p-4">Phone</th>
                <th className="text-right p-4">Balance</th>
                {canManage && <th className="p-4" />}
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={5} className="p-6 text-center text-muted">
                    Loading…
                  </td>
                </tr>
              ) : members.length === 0 ? (
                <tr>
                  <td colSpan={5} className="p-6 text-center text-muted">
                    No members yet. Add your first member to start collections.
                  </td>
                </tr>
              ) : (
                members.map((m) => (
                  <tr key={m.id} className="border-b border-border/50 hover:bg-surface-overlay/50">
                    <td className="p-4 font-mono">{m.memberNumber}</td>
                    <td className="p-4">{m.fullName}</td>
                    <td className="p-4 font-mono text-muted">{m.phone}</td>
                    <td className="p-4 text-right font-mono text-emerald-400">
                      {formatMoney(m.balance_minor, "ugx")}
                    </td>
                    {canManage && (
                      <td className="p-4 text-right">
                        <button
                          type="button"
                          onClick={() => {
                            setCollectResult(null);
                            setCollectMember(m);
                          }}
                          className="text-xs px-3 py-1.5 rounded bg-emerald-600/20 text-emerald-400 border border-emerald-500/30"
                        >
                          Collect
                        </button>
                      </td>
                    )}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </main>

      {showAdd && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center p-4 z-50">
          <form onSubmit={handleAdd} className="bg-surface-raised border border-border rounded-xl p-6 w-full max-w-md space-y-4">
            <h2 className="font-semibold">Add member</h2>
            <input
              required
              placeholder="Member number"
              value={form.member_number}
              onChange={(e) => setForm({ ...form, member_number: e.target.value })}
              className="w-full bg-surface-overlay border border-border rounded-lg px-3 py-2 text-sm"
            />
            <input
              required
              placeholder="Full name"
              value={form.full_name}
              onChange={(e) => setForm({ ...form, full_name: e.target.value })}
              className="w-full bg-surface-overlay border border-border rounded-lg px-3 py-2 text-sm"
            />
            <input
              required
              placeholder="Phone (+256…)"
              value={form.phone}
              onChange={(e) => setForm({ ...form, phone: e.target.value })}
              className="w-full bg-surface-overlay border border-border rounded-lg px-3 py-2 text-sm"
            />
            <select
              value={form.momo_network}
              onChange={(e) => setForm({ ...form, momo_network: e.target.value })}
              className="w-full bg-surface-overlay border border-border rounded-lg px-3 py-2 text-sm"
            >
              <option value="MTN">MTN MoMo</option>
              <option value="AIRTEL">Airtel Money</option>
            </select>
            <div className="flex gap-2 justify-end">
              <button type="button" onClick={() => setShowAdd(false)} className="text-sm text-muted px-3 py-2">
                Cancel
              </button>
              <button type="submit" className="bg-emerald-600 hover:bg-emerald-500 px-4 py-2 rounded-lg text-sm">
                Save
              </button>
            </div>
          </form>
        </div>
      )}

      {collectMember && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center p-4 z-50">
          <form onSubmit={handleCollect} className="bg-surface-raised border border-border rounded-xl p-6 w-full max-w-md space-y-4">
            <h2 className="font-semibold">Collect from {collectMember.fullName}</h2>
            {collectResult ? (
              <div className="space-y-3">
                <p className="text-emerald-400 text-sm">{collectResult.message}</p>
                <p className="text-xs text-muted">Intent: {collectResult.intentId}</p>
                <button
                  type="button"
                  onClick={() => setCollectMember(null)}
                  className="w-full bg-surface-overlay border border-border rounded-lg py-2 text-sm"
                >
                  Close
                </button>
              </div>
            ) : (
              <>
                <select name="product_id" className="w-full bg-surface-overlay border border-border rounded-lg px-3 py-2 text-sm">
                  <option value="">Custom amount</option>
                  {products.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name} — {formatMoney(p.amountMinor, "ugx")}
                    </option>
                  ))}
                </select>
                <input
                  name="amount_minor"
                  type="number"
                  min={1000}
                  placeholder="Amount UGX (if custom)"
                  className="w-full bg-surface-overlay border border-border rounded-lg px-3 py-2 text-sm"
                />
                <input
                  name="purpose"
                  placeholder="Purpose e.g. DUES_2026_06"
                  className="w-full bg-surface-overlay border border-border rounded-lg px-3 py-2 text-sm"
                />
                <p className="text-xs text-muted">Member will receive an MoMo prompt on {collectMember.phone}</p>
                <div className="flex gap-2 justify-end">
                  <button type="button" onClick={() => setCollectMember(null)} className="text-sm text-muted px-3 py-2">
                    Cancel
                  </button>
                  <button type="submit" className="bg-emerald-600 hover:bg-emerald-500 px-4 py-2 rounded-lg text-sm">
                    Send MoMo prompt
                  </button>
                </div>
              </>
            )}
          </form>
        </div>
      )}
    </div>
  );
}
