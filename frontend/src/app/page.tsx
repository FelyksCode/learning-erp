import type { CSSProperties } from "react";
import AdvisorNote from "@/components/AdvisorNote";
import SalesChart from "@/components/SalesChart";
import { apiGet } from "@/lib/api-server";
import type { AIInsights, Overview, RestockRow, TrendPoint } from "@/lib/api";

const STAMP_WORDS: Record<string, string> = {
  "out-of-stock": "Order now",
  low: "Reorder",
  "no-sales": "Not moving",
  ok: "In cover",
  "not-tracked": "\u2014",
};

const STAMP_TONE: Record<string, string> = {
  "out-of-stock": "border-stamp text-stamp",
  low: "border-stamp text-stamp",
  "no-sales": "border-pencil text-pencil",
  ok: "border-ink/60 text-ink",
  "not-tracked": "border-rule text-pencil",
};

function stampTilt(status: string): string {
  if (status === "low") return "1.5deg";
  if (status === "out-of-stock") return "-2deg";
  return "0deg";
}

// Backend serializes Decimal as JSON strings — coerce every numeric field once, here.
const num = (v: number | string | null | undefined): number => Number(v ?? 0);

function money(n: number | string) {
  return num(n).toLocaleString(undefined, { style: "currency", currency: "USD", maximumFractionDigits: 2 });
}

function Counter({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="px-4 py-3">
      <p className="font-display text-[10px] font-semibold uppercase tracking-[0.18em] text-pencil">{label}</p>
      <p className="mt-1 font-mono text-[22px] font-medium tabular-nums leading-none text-ink">{value}</p>
      {hint && <p className="mt-1 font-mono text-[10px] text-pencil">{hint}</p>}
    </div>
  );
}

export default async function DashboardPage() {
  const [overview, restock, trend, ai] = await Promise.all([
    apiGet<Overview>("/analytics/overview"),
    apiGet<RestockRow[]>("/analytics/restock"),
    apiGet<TrendPoint[]>("/analytics/sales-trend?days=30"),
    apiGet<AIInsights>("/ai/insights").catch(() => ({ enabled: false }) as AIInsights),
  ]);

  const needsAttention = restock.filter((r) => r.status === "low" || r.status === "out-of-stock");
  const points = trend.map((t) => ({
    date: t.date,
    qty_sold: num(t.qty_sold),
    revenue: num(t.revenue),
  }));

  return (
    <div className="space-y-10">
      <section aria-label="Today at a glance">
        <p className="eyebrow mb-2">Today at a glance</p>
        <div className="doc-panel grid grid-cols-2 divide-x divide-y divide-rule md:grid-cols-5 md:divide-y-0">
          <Counter label="Active SKUs" value={String(overview.active_products)} />
          <Counter label="Stock value" value={money(overview.stock_value)} hint="at cost" />
          <Counter
            label="To review"
            value={String(overview.low_stock_count)}
            hint={`${overview.out_of_stock_count} out of stock`}
          />
          <Counter label="Revenue today" value={money(overview.revenue_today)} />
          <Counter label="Revenue 30d" value={money(overview.revenue_30d)} hint={`7d · ${money(overview.revenue_7d)}`} />
        </div>
      </section>

      <section aria-label="Restock list">
        <div className="mb-2 flex items-baseline justify-between">
          <p className="eyebrow">Restock list</p>
          {needsAttention.length > 0 && (
            <p className="font-mono text-[11px] uppercase tracking-[0.14em] text-stamp">
              {needsAttention.length} item{needsAttention.length > 1 ? "s" : ""} to order
            </p>
          )}
        </div>
        <div className="doc-panel overflow-x-auto">
          <table className="w-full min-w-[680px] text-sm">
            <thead>
              <tr className="border-b border-kraft text-left">
                <th className="eyebrow px-4 pb-2 pt-3">Item</th>
                <th className="eyebrow px-4 pb-2 pt-3 text-right">On hand</th>
                <th className="eyebrow px-4 pb-2 pt-3 text-right">Sold / day</th>
                <th className="eyebrow px-4 pb-2 pt-3 text-right">Cover</th>
                <th className="eyebrow px-4 pb-2 pt-3 text-right">Reorder at</th>
                <th className="eyebrow px-4 pb-2 pt-3 text-right">Order qty</th>
                <th className="eyebrow px-4 pb-2 pt-3">Verdict</th>
              </tr>
            </thead>
            <tbody>
              {restock.map((row, index) => {
                const isUrgent = row.status === "out-of-stock";
                return (
                  <tr
                    key={row.product_id}
                    className={`border-b border-rule last:border-b-0 ${isUrgent ? "bg-stamp/[0.04]" : ""}`}
                  >
                    <td className="max-w-[240px] truncate px-4 py-2.5">
                      <span className="mr-2 font-mono text-xs text-pencil">{row.sku}</span>
                      <span className="font-medium text-ink">{row.name}</span>
                    </td>
                    <td className="px-4 py-2.5 text-right font-mono tabular-nums text-ink">{num(row.on_hand)}</td>
                    <td className="px-4 py-2.5 text-right font-mono tabular-nums text-ink">
                      {num(row.avg_daily_sales).toFixed(1)}
                    </td>
                    <td className="px-4 py-2.5 text-right font-mono tabular-nums text-ink">
                      {row.days_of_cover == null ? "\u2014" : `${num(row.days_of_cover).toFixed(0)}d`}
                    </td>
                    <td className="px-4 py-2.5 text-right font-mono tabular-nums text-pencil">
                      {num(row.reorder_point).toFixed(0)}
                    </td>
                    <td className="px-4 py-2.5 text-right">
                      {num(row.suggested_order_qty) > 0 ? (
                        <span
                          className="inline-flex h-8 w-8 -rotate-3 items-center justify-center rounded-full border-[1.5px] border-biro font-mono text-[13px] font-semibold text-biro"
                          title="Suggested order quantity"
                        >
                          {num(row.suggested_order_qty)}
                        </span>
                      ) : (
                        <span className="text-pencil">{"\u2014"}</span>
                      )}
                    </td>
                    <td className="whitespace-nowrap px-4 py-2.5">
                      <span
                        className={`stamp stamp-animated ${STAMP_TONE[row.status] ?? ""}`}
                        style={
                          {
                            "--stamp-tilt": stampTilt(row.status),
                            animationDelay: `${Math.min(index * 45, 400)}ms`,
                          } as CSSProperties
                        }
                      >
                        {STAMP_WORDS[row.status] ?? row.status}
                      </span>
                    </td>
                  </tr>
                );
              })}
              {restock.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-sm text-pencil">
                    No products yet. Add items on the Products page to build your restock list.
                  </td>
                </tr>
              )}
              {restock.length > 0 && needsAttention.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-4 py-3 text-center text-xs text-pencil">
                    Nothing needs ordering right now — every tracked item sits above its reorder point.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        <p className="mt-2 font-mono text-[10px] uppercase tracking-[0.12em] text-pencil">
          Reorder point = lead time × avg daily sales (30d) + safety stock · Order qty covers lead time + 7 days
        </p>
      </section>

      <AdvisorNote initial={ai} />

      <section aria-label="Sales, last 30 days">
        <p className="eyebrow mb-2">Sales · last 30 days</p>
        <div className="doc-panel h-64 p-4">
          <SalesChart trend={points} />
        </div>
      </section>
    </div>
  );
}
