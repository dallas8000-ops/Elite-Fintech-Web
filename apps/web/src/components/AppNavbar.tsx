import { Link, NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { getAdminUrl } from "../lib/api";
function linkClass({ isActive }: { isActive: boolean }) {
  return [
    "transition-colors",
    isActive ? "text-white font-medium" : "text-muted hover:text-white",
  ].join(" ");
}

export default function AppNavbar() {
  const { user, role, logout } = useAuth();
  const navigate = useNavigate();
  const canManage = role === "OWNER" || role === "ADMIN";

  const handleSignOut = () => {
    logout();
    navigate("/");
  };

  return (
    <header className="border-b border-border bg-surface-raised/80 backdrop-blur sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between gap-6">
        <Link
          to={user ? "/dashboard" : "/"}
          className="flex items-center gap-3 shrink-0 hover:opacity-90 transition-opacity"
        >
          <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-brand-600 to-emerald-600 flex items-center justify-center font-bold text-sm">
            EF
          </div>
          <span className="font-semibold hidden sm:inline">Elite Fintech Systems</span>
        </Link>

        <nav className="flex items-center gap-4 sm:gap-6 text-sm">
          {user ? (
            <>
              <NavLink to="/dashboard" className={linkClass}>
                Dashboard
              </NavLink>
              <NavLink to="/members" className={linkClass}>
                Members
              </NavLink>
              <NavLink to="/collections" className={linkClass}>
                Collections
              </NavLink>
              <NavLink to="/settings" className={linkClass}>
                Settings
              </NavLink>
              <NavLink to="/setup" className={linkClass}>
                Domain setup
              </NavLink>
              {canManage && (
                <a
                  href={getAdminUrl()}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-muted hover:text-white transition-colors"
                >
                  Admin ↗
                </a>
              )}
              <button
                type="button"
                onClick={handleSignOut}
                className="text-muted hover:text-white transition-colors"
              >
                Sign out
              </button>
            </>
          ) : (
            <>
              <NavLink to="/" end className={linkClass}>
                Home
              </NavLink>
              <NavLink to="/login" className={linkClass}>
                Sign in
              </NavLink>
              <Link
                to="/register"
                className="bg-brand-600 hover:bg-brand-500 px-4 py-2 rounded-lg font-medium text-white transition-colors"
              >
                Get started
              </Link>
            </>
          )}
        </nav>
      </div>
    </header>
  );
}
