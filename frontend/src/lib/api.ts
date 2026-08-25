const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";

const TOKEN_KEY = "erp_token";

export function getToken(): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(new RegExp(`(?:^|; )${TOKEN_KEY}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

export function setToken(token: string): void {
  document.cookie = `${TOKEN_KEY}=${encodeURIComponent(token)}; path=/; max-age=604800; samesite=lax`;
}

export function clearToken(): void {
  document.cookie = `${TOKEN_KEY}=; path=/; max-age=0`;
}

function authHeaders(): Record<string, string> {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export type Overview = {
  active_products: number;
  stock_value: number;
  low_stock_count: number;
  out_of_stock_count: number;
  revenue_today: number;
  revenue_7d: number;
  revenue_30d: number;
};

export type RestockRow = {
  product_id: number;
  sku: string;
  name: string;
  on_hand: number;
  avg_daily_sales: number;
  days_of_cover: number | null;
  reorder_point: number;
  suggested_order_qty: number;
  status: string;
};

export type TrendPoint = { date: string; qty_sold: number; revenue: number };

export type AIInsights = {
  enabled: boolean;
  insight?: string;
  reason?: string;
};

export type Product = {
  id: number;
  sku: string;
  barcode: string | null;
  name: string;
  category_id: number | null;
  unit_cost: number;
  sale_price: number;
  reorder_enabled: boolean;
  lead_time_days: number;
  safety_stock: number;
  is_active: boolean;
  on_hand: number;
};

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    if (res.status === 401 && typeof window !== "undefined") {
      clearToken();
      // eslint-disable-next-line @next/next/no-location-assign-relative-destination -- full reload is intentional: clears all cached client state after auth loss
      window.location.assign("/login");
    }
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {}
    throw new ApiError(res.status, detail);
  }
  return res.json();
}

export function get<T>(path: string): Promise<T> {
  return fetch(`${API}${path}`, { headers: authHeaders() }).then((r) => handle<T>(r));
}

export function post<T>(path: string, body?: unknown): Promise<T> {
  return fetch(`${API}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(body ?? {}),
  }).then((r) => handle<T>(r));
}
