import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from "react";
import { api, type AuthUser, type Organization, type OrganizationUpdatePayload, type RegisterPayload } from "../lib/api";

interface AuthState {
  user: AuthUser | null;
  organization: Organization | null;
  role: string | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (data: RegisterPayload) => Promise<void>;
  updateOrganization: (data: OrganizationUpdatePayload) => Promise<Organization>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [organization, setOrganization] = useState<Organization | null>(null);
  const [role, setRole] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const loadSession = useCallback(async () => {
    const token = localStorage.getItem("token");
    if (!token) {
      setLoading(false);
      return;
    }
    try {
      const data = await api.me();
      setUser(data.user);
      setOrganization(data.organization);
      setRole(data.role);
    } catch {
      localStorage.removeItem("token");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadSession();
  }, [loadSession]);

  const login = async (email: string, password: string) => {
    const data = await api.login({ email, password });
    localStorage.setItem("token", data.token);
    setUser(data.user);
    setOrganization(data.organization);
    setRole(data.role);
  };

  const register = async (form: RegisterPayload) => {
    const data = await api.register(form);
    localStorage.setItem("token", data.token);
    setUser(data.user);
    setOrganization(data.organization);
    setRole(data.role);
  };

  const updateOrganization = async (payload: OrganizationUpdatePayload) => {
    const data = await api.updateOrganization(payload);
    setOrganization(data.organization);
    return data.organization;
  };

  const logout = () => {
    localStorage.removeItem("token");
    setUser(null);
    setOrganization(null);
    setRole(null);
  };

  return (
    <AuthContext.Provider value={{ user, organization, role, loading, login, register, updateOrganization, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
