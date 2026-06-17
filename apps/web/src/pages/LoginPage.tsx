import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import AppNavbar from "../components/AppNavbar";
import { useAuth } from "../context/AuthContext";

import { DEMO_EMAIL, DEMO_PASSWORD } from "../lib/demo";

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState(DEMO_EMAIL);
  const [password, setPassword] = useState(DEMO_PASSWORD);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(email, password);
      navigate("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen">
      <AppNavbar />
      <div className="flex items-center justify-center px-4 py-12">
        <div className="w-full max-w-md">
          <div className="text-center mb-8">
            <p className="text-muted">Sign in to your organisation</p>
          </div>

          <form onSubmit={handleSubmit} className="bg-surface-raised border border-border rounded-2xl p-8 space-y-5">
            {error && (
              <div className="bg-red-500/10 border border-red-500/30 text-red-400 text-sm rounded-lg px-4 py-3">
                {error}
              </div>
            )}

            <div>
              <label className="block text-sm font-medium text-muted mb-1.5">Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full bg-surface-overlay border border-border rounded-lg px-4 py-2.5 text-white focus:outline-none focus:ring-2 focus:ring-brand-500/50"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-muted mb-1.5">Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full bg-surface-overlay border border-border rounded-lg px-4 py-2.5 text-white focus:outline-none focus:ring-2 focus:ring-brand-500/50"
                required
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-brand-600 hover:bg-brand-500 disabled:opacity-50 text-white font-medium rounded-lg py-2.5 transition-colors"
            >
              {loading ? "Signing in…" : "Sign in"}
            </button>

            <Link
              to="/demo"
              className="block w-full text-center border border-emerald-500/40 text-emerald-400 hover:bg-emerald-500/10 font-medium rounded-lg py-2.5 transition-colors"
            >
              Open live demo
            </Link>

            <p className="text-center text-sm text-muted">
              No account?{" "}
              <Link to="/register" className="text-brand-400 hover:text-brand-300">
                Register
              </Link>
            </p>
          </form>
        </div>
      </div>
    </div>
  );
}

