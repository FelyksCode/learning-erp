import ProductForm, { ProductActions, ProductToolbar } from "@/components/ProductPanels";
import { apiGet } from "@/lib/api-server";
import type { Product } from "@/lib/api";

export default async function ProductsPage() {
  const products = await apiGet<Product[]>("/products");

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="font-display text-lg font-bold uppercase tracking-[0.08em] text-ink">Product book</h1>
        <ProductToolbar />
      </div>

      <ProductForm />

      <div className="doc-panel overflow-x-auto">
        <table className="w-full min-w-[600px] text-sm">
          <thead>
            <tr className="border-b border-kraft text-left">
              <th className="eyebrow px-4 pb-2 pt-3">SKU</th>
              <th className="eyebrow px-4 pb-2 pt-3">Name</th>
              <th className="eyebrow px-4 pb-2 pt-3 text-right">Cost (Rp)</th>
              <th className="eyebrow px-4 pb-2 pt-3 text-right">Price (Rp)</th>
              <th className="eyebrow px-4 pb-2 pt-3 text-right">On hand</th>
              <th className="eyebrow px-4 pb-2 pt-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {products.map((p) => (
              <tr
                key={p.id}
                className={`border-b border-rule last:border-b-0 ${p.on_hand <= 0 ? "bg-stamp/[0.04]" : ""}`}
              >
                <td className="whitespace-nowrap px-4 py-2.5 font-mono text-xs text-pencil">{p.sku}</td>
                <td className="px-4 py-2.5 font-medium text-ink">{p.name}</td>
                <td className="px-4 py-2.5 text-right font-mono tabular-nums text-pencil">
                  {Number(p.unit_cost).toFixed(2)}
                </td>
                <td className="px-4 py-2.5 text-right font-mono tabular-nums text-pencil">
                  {Number(p.sale_price).toFixed(2)}
                </td>
                <td
                  className={`px-4 py-2.5 text-right font-mono font-semibold tabular-nums ${
                    p.on_hand <= 0 ? "text-stamp" : "text-ink"
                  }`}
                >
                  {p.on_hand}
                </td>
                <td className="whitespace-nowrap px-4 py-2.5 text-right">
                  <ProductActions product={p} />
                </td>
              </tr>
            ))}
            {products.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-sm text-pencil">
                  No products yet. Add your first item above, or import a CSV.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
