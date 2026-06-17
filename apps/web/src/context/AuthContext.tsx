import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from "react";
import { api, setAccessToken, getAccessToken, type AuthUser, type Organization, type OrganizationUpdatePayload, type RegisterPayload } from "../lib/api";

interface AuthState {
  user: AuthUser | null;
  organization: Organization | null;
  role: string | null;
  accessToken: string | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (data: RegisterPayload) => Promise<void>;
  updateOrganization: (data: OrganizationUpdatePayload) => Promise<Organization>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [organization, setOrganization] = useState<Organization | null>(null);
  const [role, setRole] = useState<string | null>(null);
  const [accessToken, setAccessTokenState] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const loadSession = useCallback(async () => {
    try {
      if (!getAccessToken()) {
        const refreshed = await api.refreshSession();
        if (!refreshed) {
          return;
        }
      }
      const data = await api.me();
      setUser(data.user);
      setOrganization(data.organization);
      setRole(data.role);
      setAccessTokenState(getAccessToken());
    } catch {
      setAccessToken(null);
      setAccessTokenState(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadSession();
  }, [loadSession]);

  const login = async (email: string, password: string) => {
    const data = await api.login({ email, password });
    setUser(data.user);
    setOrganization(data.organization);
    setRole(data.role);
    setAccessTokenState(getAccessToken());
  };

  const register = async (form: RegisterPayload) => {
    const data = await api.register(form);
    setUser(data.user);
    setOrganization(data.organization);
    setRole(data.role);
    setAccessTokenState(getAccessToken());
  };

  const updateOrganization = async (payload: OrganizationUpdatePayload) => {
    const data = await api.updateOrganization(payload);
    setOrganization(data.organization);
    return data.organization;
  };

  const logout = async () => {
    await api.logout();
    setUser(null);
    setOrganization(null);
    setRole(null);
    setAccessTokenState(null);
  };

  return (
    <AuthContext.Provider
      value={{ user, organization, role, accessToken, loading, login, register, updateOrganization, logout }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
