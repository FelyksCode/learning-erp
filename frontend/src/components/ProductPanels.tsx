"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { post, type Product } from "@/lib/api";

const EMPTY_FORM = { sku: "", name: "", unit_cost: "", sale_price: "" };

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1 block font-display text-[10px] font-semibold uppercase tracking-[0.18em] text-pencil">
        {label}
      </span>
      {children}
    </label>
  );
}

export default function ProductForm() {
  const router = useRouter();
  const [form, setForm] = useState(EMPTY_FORM);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await post("/products", {
        sku: form.sku,
        name: form.name,
        unit_cost: form.unit_cost || "0",
        sale_price: form.sale_price || "0",
      });
      setForm(EMPTY_FORM);
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="doc-panel px-4 py-4 sm:px-5">
      <p className="eyebrow mb-4">New item · stock intake</p>
      <div className="grid grid-cols-2 gap-x-6 gap-y-4 sm:grid-cols-5">
        <Field label="SKU">
          <input
            required
            value={form.sku}
            onChange={(e) => setForm({ ...form, sku: e.target.value })}
            className="ledger-input w-full font-mono uppercase"
            placeholder="SKU-001"
          />
        </Field>
        <Field label="Name">
          <input
            required
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            className="ledger-input w-full sm:col-span-2"
            placeholder="What you call it on the shelf"
          />
        </Field>
        <Field label="Cost">
          <input
            type="number"
            step="0.01"
            min="0"
            value={form.unit_cost}
            onChange={(e) => setForm({ ...form, unit_cost: e.target.value })}
            className="ledger-input w-full text-right font-mono tabular-nums"
            placeholder="0.00"
          />
        </Field>
        <Field label="Price">
          <input
            type="number"
            step="0.01"
            min="0"
            value={form.sale_price}
            onChange={(e) => setForm({ ...form, sale_price: e.target.value })}
            className="ledger-input w-full text-right font-mono tabular-nums"
            placeholder="0.00"
          />
        </Field>
      </div>
      {error && <p className="mt-3 border-l-4 border-stamp bg-stamp/[0.06] px-3 py-2 text-sm text-ink">{error}</p>}
      <button
        type="submit"
        disabled={busy}
        className="mt-4 rounded-sm bg-biro px-4 py-2 font-display text-[13px] font-semibold uppercase tracking-[0.12em] text-paper hover:bg-ink disabled:opacity-50"
      >
        Add product
      </button>
    </form>
  );
}

export function ProductActions({ product }: { product: Product }) {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);

  async function receive() {
    const qty = window.prompt(`Receive stock for ${product.sku} — quantity?`);
    if (!qty) return;
    const cost = window.prompt("Unit cost?", String(product.unit_cost));
    try {
      await post("/stock-moves", {
        product_id: product.id,
        to_location_code: "SHOP",
        quantity: qty,
        unit_cost: cost ?? undefined,
        reference: "MANUAL",
      });
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setTimeout(() => setError(null), 4000);
    }
  }

  async function sell() {
    const qty = window.prompt(`Record a sale for ${product.sku} — quantity?`);
    if (!qty) return;
    try {
      await post("/sales", { lines: [{ product_id: product.id, quantity: qty }] });
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setTimeout(() => setError(null), 4000);
    }
  }

  return (
    <>
      {error && <p className="mr-2 inline text-xs text-stamp">{error}</p>}
      <button
        onClick={receive}
        className="mr-1 rounded-sm border border-ink/30 px-2 py-1 font-display text-[11px] font-semibold uppercase tracking-[0.1em] text-ink hover:bg-manila"
      >
        Receive
      </button>
      <button
        onClick={sell}
        className="rounded-sm bg-biro px-2 py-1 font-display text-[11px] font-semibold uppercase tracking-[0.1em] text-paper hover:bg-ink"
      >
        Sell
      </button>
    </>
  );
}

export function ProductToolbar() {
  const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";
  const router = useRouter();
  const [importing, setImporting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);

  async function importCsv(file: File) {
    setImporting(true);
    setMessage(null);
    const body = new FormData();
    body.append("file", file);
    try {
      const res = await fetch(`${API}/import/products`, { method: "POST", body });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail ?? res.statusText);
      setMessage(`${data.created} created · ${data.updated} updated · ${data.skipped} skipped`);
      router.refresh();
    } catch (err) {
      setFailed(true);
      setMessage(err instanceof Error ? err.message : String(err));
    } finally {
      setImporting(false);
    }
  }

  return (
    <div className="flex items-center gap-3 font-mono text-xs uppercase tracking-[0.12em]">
      {message && (
        <span className={`normal-case ${failed ? "text-stamp" : "text-pencil"}`}>{message}</span>
      )}
      <a
        href={`${API}/export/products.csv`}
        className="rounded-sm border border-ink/30 px-3 py-1.5 text-ink hover:bg-manila"
      >
        Export CSV
      </a>
      <label className="cursor-pointer rounded-sm border border-ink/30 px-3 py-1.5 text-ink hover:bg-manila">
        {importing ? "Importing…" : "Import CSV"}
        <input
          type="file"
          accept=".csv"
          className="hidden"
          disabled={importing}
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) importCsv(f);
            e.target.value = "";
          }}
        />
      </label>
    </div>
  );
}
