const API_BASE = import.meta.env.VITE_API_URL ?? "";

export interface AuthUser {
  id: string;
  email: string;
  name: string;
}

export interface Organization {
  id: string;
  name: string;
  slug: string;
  country?: string;
  province?: string;
  industry_sector?: string;
  cipc_registration_number?: string;
  vat_number?: string;
  fica_status?: string;
  popia_consent_at?: string;
}

export interface SaPlan {
  tier: string;
  label: string;
  label_af?: string | null;
  amount_cents: number;
  amount_display?: string;
  vat_inclusive: boolean;
  description: string;
  features: string[];
  currency: string;
  country?: string;
  recommended_rails: string[];
  providers?: string[];
  pricing_mode?: string;
  fx_trading_date?: string;
  fx_source?: string;
}

export interface RegionConfig {
  market: string;
  label: string;
  note: string;
  default_country: string;
  pricing?: {
    enabled: boolean;
    pricing_mode: string;
    base_currency: string;
    trading_date?: string;
    source?: string;
    fetched_at?: string;
    rates?: Record<string, number>;
  };
  countries: {
    code: string;
    label: string;
    currency: string;
    currency_label: string;
    plans: SaPlan[];
  }[];
  registration: {
    consent_label: string;
    company_reg_label: string;
    vat_label: string;
    compliance_body: string;
    region_label: string;
  };
  regions: { value: string; label: string }[];
  usd_anchors?: Record<string, number>;
}

export interface PaymentRailInfo {
  id: string;
  label: string;
  region: string;
  settlement: string;
  typical_use: string;
  western_equivalent: string | null;
  is_async: boolean;
  available: boolean;
  checkout_providers: string[];
}

export interface Subscription {
  id: string;
  planTier: string;
  status: string;
  currentPeriodEnd: string;
  cancelAtPeriodEnd: boolean;
  payment_provider?: string;
}

export interface PaymentEvent {
  id: string;
  type: string;
  amount: number | null;
  vat_amount?: number | null;
  currency: string | null;
  payment_provider?: string | null;
  payment_rail?: string | null;
  settlementStatus?: string;
  createdAt: string;
  metadata?: Record<string, unknown>;
}

export interface BillingStats {
  subscription: Subscription | null;
  totalEvents: number;
  totalRevenue: number;
  currency?: string;
  country?: string;
}

export interface PlatformCapabilities {
  tier: string;
  name: string;
  tagline: string;
  region: string;
  capabilities: { id: string; label: string; included: boolean; note: string }[];
  comparison: Record<string, number>;
  setup_api?: string;
}

export interface SetupManifest {
  platform_tier: string;
  transfer_token: string;
  target_domain: string;
  urls: Record<string, string>;
  dns_records: Record<string, { type: string; host: string; value: string; ttl: number; purpose: string }[]>;
  environment: Record<string, string>;
  setup_steps: { id: string; label: string; done: boolean }[];
  automation: {
    compatible_agents: string[];
    apply_endpoint: string;
    domains_endpoint: string;
    verify_endpoint: string;
    openapi: string;
    instructions?: string;
  };
  webhook_urls: Record<string, string>;
  message?: string;
  organization?: { id: string; name: string; slug: string };
}

export interface RegisterPayload {
  email: string;
  password: string;
  name: string;
  organization_name: string;
  country: string;
  province: string;
  industry_sector?: string;
  cipc_registration_number?: string;
  vat_number?: string;
  data_consent: boolean;
}

function getToken(): string | null {
  return localStorage.getItem("token");
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) headers.Authorization = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ error: res.statusText }));
    throw new Error(body.error ?? "Request failed");
  }

  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  register: (data: RegisterPayload) =>
    request<{ token: string; user: AuthUser; organization: Organization; role: string }>(
      "/api/v1/auth/register/",
      { method: "POST", body: JSON.stringify(data) }
    ),

  login: (data: { email: string; password: string }) =>
    request<{ token: string; user: AuthUser; organization: Organization; role: string }>(
      "/api/v1/auth/login/",
      { method: "POST", body: JSON.stringify(data) }
    ),

  me: () =>
    request<{ user: AuthUser; organization: Organization; role: string }>("/api/v1/auth/me/"),

  getRegion: (country?: string) =>
    request<RegionConfig>(`/api/v1/billing/region/${country ? `?country=${country}` : ""}`),

  getPlans: () => request<{ market: string; country: string; currency: string; plans: SaPlan[] }>("/api/v1/billing/plans/"),

  getRails: () =>
    request<{
      rails: PaymentRailInfo[];
      markets: { id: string; label: string; primary_rails: string[]; note: string }[];
      philosophy: string;
    }>("/api/v1/billing/rails/"),

  getStats: () => request<BillingStats>("/api/v1/billing/stats/"),

  getEvents: () => request<{ events: PaymentEvent[] }>("/api/v1/billing/events/"),

  checkout: (tier: string, rail: string, provider?: string) =>
    request<{ url: string; provider: string; rail: string; settlement_note?: string }>(
      "/api/v1/billing/checkout/",
      {
        method: "POST",
        body: JSON.stringify({ tier, rail, provider }),
      }
    ),

  portal: () => request<{ url: string }>("/api/v1/billing/portal/", { method: "POST" }),

  getMembers: () =>
    request<{ members: { id: string; role: string; user: AuthUser; created_at: string }[] }>(
      "/api/v1/org/members/"
    ),

  getCapabilities: () => request<PlatformCapabilities>("/api/v1/platform/capabilities/"),

  getSetup: () => request<SetupManifest>("/api/v1/platform/setup/"),

  applySetup: (data: {
    target_domain: string;
    transfer_token?: string;
    api_subdomain?: string;
    app_subdomain?: string;
    automation_agent?: string;
    completed_steps?: string[];
  }) =>
    request<SetupManifest>("/api/v1/platform/setup/apply/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  verifyDomain: (hostname: string, verification_token: string) =>
    request<{ verified: boolean; hostname: string }>("/api/v1/platform/domains/verify/", {
      method: "POST",
      body: JSON.stringify({ hostname, verification_token }),
    }),
};

export function getWsUrl(token: string): string {
  const base = import.meta.env.VITE_WS_URL;
  if (base) return `${base}?token=${token}`;
  const proto = window.location.protocol === "https:" ? "wss" : "ws";
  return `${proto}://${window.location.host}/ws/billing/?token=${token}`;
}

export function formatMoney(amountMinor: number | null, currency = "ugx"): string {
  if (amountMinor == null) return "—";
  const cur = currency.toLowerCase();
  if (cur === "zar") {
    return new Intl.NumberFormat("en-ZA", { style: "currency", currency: "ZAR" }).format(amountMinor / 100);
  }
  if (cur === "kes") {
    return new Intl.NumberFormat("en-KE", { style: "currency", currency: "KES" }).format(amountMinor / 100);
  }
  if (cur === "ugx") return `USh ${amountMinor.toLocaleString("en-UG")}`;
  if (cur === "rwf") return `FRw ${amountMinor.toLocaleString("en-RW")}`;
  if (cur === "tzs") return `TSh ${amountMinor.toLocaleString("en-TZ")}`;
  return `${amountMinor.toLocaleString()} ${currency.toUpperCase()}`;
}

/** @deprecated use formatMoney */
export function formatZar(cents: number | null): string {
  return formatMoney(cents, "zar");
}

export const EAST_AFRICA_COUNTRIES = [
  { value: "UG", label: "Uganda" },
  { value: "KE", label: "Kenya" },
  { value: "RW", label: "Rwanda" },
  { value: "TZ", label: "Tanzania" },
];

export const SA_PROVINCES = [
  { value: "GAUTENG", label: "Gauteng" },
  { value: "WESTERN_CAPE", label: "Western Cape" },
  { value: "KWAZULU_NATAL", label: "KwaZulu-Natal" },
  { value: "EASTERN_CAPE", label: "Eastern Cape" },
  { value: "LIMPOPO", label: "Limpopo" },
  { value: "MPUMALANGA", label: "Mpumalanga" },
  { value: "NORTH_WEST", label: "North West" },
  { value: "FREE_STATE", label: "Free State" },
  { value: "NORTHERN_CAPE", label: "Northern Cape" },
];

export const INDUSTRY_SECTORS = [
  "Banking & Lending",
  "Payments & Wallets",
  "Insurtech",
  "Wealth & Asset Management",
  "RegTech & Compliance",
  "SME & Merchant Services",
  "Other",
];

export const PAYMENT_RAIL_LABELS: Record<string, string> = {
  CARD: "Card",
  EFT: "Standard EFT",
  INSTANT_EFT: "Instant EFT",
  DEBIT_ORDER: "Debit Order (DebiCheck)",
  PAYSHAP: "PayShap",
  RNCS: "Capitec Pay",
  MOBILE_MONEY: "Mobile Money",
  USSD: "USSD",
  AGENT_CASH: "Agent Cash",
};

export const EVENT_LABELS: Record<string, string> = {
  SUBSCRIPTION_CREATED: "Subscription created",
  SUBSCRIPTION_UPDATED: "Subscription updated",
  SUBSCRIPTION_CANCELED: "Subscription canceled",
  INVOICE_PAID: "Invoice paid",
  INVOICE_FAILED: "Invoice failed",
  PAYMENT_SUCCEEDED: "Payment succeeded",
  PAYMENT_FAILED: "Payment failed",
  CHECKOUT_COMPLETED: "Checkout completed",
  EFT_PENDING: "EFT pending (1–3 days)",
  PAYSHAP_RECEIVED: "PayShap received",
};
