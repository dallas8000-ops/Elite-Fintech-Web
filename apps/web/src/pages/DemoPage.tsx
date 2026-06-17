import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import AppNavbar from "../components/AppNavbar";
import { useAuth } from "../context/AuthContext";
import { DEMO_EMAIL, DEMO_PASSWORD } from "../lib/demo";

export default function DemoPage() {
  const { login, user, loading } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState("");

  useEffect(() => {
    if (loading) return;
    if (user) {
      navigate("/dashboard", { replace: true });
      return;
    }

    let cancelled = false;
    void login(DEMO_EMAIL, DEMO_PASSWORD)
      .then(() => {
        if (!cancelled) navigate("/dashboard", { replace: true });
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Demo login failed");
        }
      });

    return () => {
      cancelled = true;
    };
  }, [loading, user, login, navigate]);

  return (
    <div className="min-h-screen">
      <AppNavbar />
      <div className="flex items-center justify-center px-4 py-24">
        <div className="w-full max-w-md text-center">
          {!error ? (
            <>
              <p className="text-lg font-medium text-white mb-2">Opening live demo…</p>
              <p className="text-sm text-muted">Signing in as Kampala Pay demo org</p>
            </>
          ) : (
            <div className="bg-surface-raised border border-border rounded-2xl p-8 space-y-4">
              <p className="text-red-400 text-sm">{error}</p>
              <p className="text-xs text-muted">
                Demo data may still be seeding on the server. Try again in a minute or sign in manually.
              </p>
              <div className="flex flex-col gap-2">
                <Link
                  to="/login"
                  className="bg-brand-600 hover:bg-brand-500 text-white font-medium rounded-lg py-2.5 transition-colors"
                >
                  Sign in manually
                </Link>
                <Link to="/" className="text-sm text-muted hover:text-white">
                  Back to home
                </Link>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
