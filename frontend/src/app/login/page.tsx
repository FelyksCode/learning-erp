"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { setToken } from "@/lib/api";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const res = await fetch(`${API}/auth/token`, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams({ username, password }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail ?? res.statusText);
      setToken(data.access_token);
      router.push("/");
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto mt-20 w-full max-w-sm">
      <div className="doc-panel border-t-4 border-t-ink p-6 sm:p-8">
        <p className="font-display text-xl font-bold uppercase tracking-[0.08em] text-ink">The Stock Ledger</p>
        <p className="mt-1 font-mono text-[10px] uppercase tracking-[0.2em] text-pencil">
          Sign in to open the book
        </p>

        <form onSubmit={submit} className="mt-7 space-y-5">
          <label className="block">
            <span className="mb-1 block font-display text-[10px] font-semibold uppercase tracking-[0.18em] text-pencil">
              Username
            </span>
            <input
              required
              autoFocus
              autoComplete="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="ledger-input w-full"
            />
          </label>
          <label className="block">
            <span className="mb-1 block font-display text-[10px] font-semibold uppercase tracking-[0.18em] text-pencil">
              Password
            </span>
            <input
              required
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="ledger-input w-full"
            />
          </label>

          {error && (
            <p className="border-l-4 border-stamp bg-stamp/[0.06] px-3 py-2 text-sm text-ink">{error}</p>
          )}

          <button
            type="submit"
            disabled={busy}
            className="w-full rounded-sm bg-biro px-4 py-2.5 font-display text-sm font-semibold uppercase tracking-[0.14em] text-paper hover:bg-ink disabled:opacity-50"
          >
            {busy ? "Opening…" : "Open the book"}
          </button>
        </form>

        <p className="mt-6 border-t border-rule pt-4 font-mono text-[10px] leading-relaxed text-pencil">
          Fresh database starts with admin / admin. Change it after your first login.
        </p>
      </div>
    </div>
  );
}
