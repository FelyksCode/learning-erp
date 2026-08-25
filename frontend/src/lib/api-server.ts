import { cookies } from "next/headers";
import { redirect } from "next/navigation";

const TOKEN_KEY = "erp_token";

// Server components run inside a container/network where the API host differs
// from the browser's view of it — hence the separate runtime-only variable.
const API =
  process.env.API_URL_SERVER ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";

export async function apiGet<T>(path: string): Promise<T> {
  const token = (await cookies()).get(TOKEN_KEY)?.value;
  const res = await fetch(`${API}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    cache: "no-store",
  });

  if (res.status === 401) redirect("/login");
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? res.statusText);
  }
  return res.json();
}
