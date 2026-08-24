# Learning ERP — Inventory Management for a Shop

Build our own inventory ERP (learning project) using **Odoo as the domain reference**: we copy its proven
concepts (products, UoM, locations, stock moves, purchase orders) but implement only what a single shop needs,
simplified for learning and full control over analytics/AI features.

## Goals

1. Track products and stock levels in one place
2. Record every stock movement (purchases in, sales out, adjustments)
3. Analytics dashboard: sales velocity, days-of-stock-left, reorder points, low-stock alerts
4. AI insights: plain-language restock recommendations from sales summaries (LLM API)
5. Learn ERP domain modeling by mirroring Odoo's architecture

## Tech Stack

| Layer      | Choice                                   | Why |
|------------|------------------------------------------|-----|
| Backend    | FastAPI + SQLAlchemy 2.x + Pydantic v2   | Matches installed skills; async, typed |
| Database   | PostgreSQL (SQLite fallback for dev)     | Real SQL analytics; easy local start |
| Migrations | Alembic                                  | Standard SQLAlchemy tooling |
| Frontend   | Next.js (App Router) + TypeScript        | Matches installed skills |
| Charts     | Recharts                                 | Simple React charting |
| Auth       | JWT (deferred — milestone 5)             | Single user first |

## Domain Model (Odoo → Ours)

Odoo concept            | Our table          | Notes
------------------------|--------------------|---------------------------------------------
`product.template`      | `categories`       | Product grouping for reports
`product.product`       | `products`         | SKU, barcode, cost, sale_price, min_stock, reorder fields
`uom.uom`               | *(skipped)*        | Assume one unit per product (add later if needed)
`res.partner`           | `partners`         | Suppliers AND customers, `type` discriminator
`stock.location`        | `locations`        | SHOP, STORAGE, SUPPLIER, CUSTOMER, LOSS (seeded)
`stock.move`            | `stock_moves`      | The heart: product, from_loc → to_loc, qty, unit_cost, ref, moved_at
`stock.quant`           | computed           | On-hand = SUM(in) - SUM(out) per product/location (view or query); no duplicate state
`purchase.order(+line)` | `purchase_orders`, `purchase_order_lines` | draft → ordered → received; receiving writes stock moves
Sales (from POS)        | `sales`, `sale_lines` | Manual entry / CSV import for now; each sale = stock move SHOP→CUSTOMER

### Key invariant
Every quantity change must be a `stock_moves` row. On-hand is always derivable — never edited directly.
This is exactly how Odoo keeps an audit trail.

## Reorder Math (deterministic layer before AI)

- `avg_daily_sales = qty sold in window W / W days` (default W=30)
- `lead_time_days` per supplier/product (configurable on product)
- `reorder_point = lead_time_days * avg_daily_sales + safety_stock`
- `days_of_cover = on_hand / avg_daily_sales` (∞ if no sales yet)
- Alert when `on_hand <= reorder_point`

## AI Insight Layer (milestone 4)

1. Backend computes deterministic stats (above) into a compact JSON summary
2. Optional LLM call (`OPENAI_API_KEY` or compatible endpoint) turns it into recommendations:
   "Restock SKU X this week (~N units), Y is slow-moving, consider promo"
3. Feature-flagged: app works fully without a key

## API Surface (v1)

```
GET/POST/PATCH    /api/products
GET               /api/products/{id}/on_hand
POST              /api/stock-moves            # manual in/out/adjust
GET               /api/stock-moves?product_id=
GET/POST          /api/partners               # suppliers/customers
GET/POST          /api/purchase-orders        # lifecycle endpoints: /order, /receive
GET/POST          /api/sales                  # + CSV import later
GET               /api/analytics/overview     # KPI cards
GET               /api/analytics/restock      # reorder report rows
GET               /api/analytics/sales-trend  # chart series
GET               /api/ai/insights            # LLM narrative (flagged)
```

## Repo Layout

```
backend/
  pyproject.toml
  alembic/
  app/
    main.py            # FastAPI app factory
    core/config.py     # settings (env-driven)
    core/db.py         # engine/session
    models/            # SQLAlchemy models (domain above)
    schemas/           # Pydantic request/response
    api/routers/       # products, partners, stock, purchases, sales, analytics, ai
    services/          # inventory logic, forecasting, ai client
frontend/              # Next.js (scaffolded in milestone 3)
PLAN.md  README.md
```

## Milestones

- **M1 — Core inventory** ✅ models + products CRUD, manual stock moves, on-hand query
- **M2 — Purchasing** ✅ PO lifecycle (draft→ordered→received), receiving auto-writes stock moves
- **M3 — Sales + Dashboard** ✅ sales with price snapshot + oversell guard; analytics endpoints
  (overview KPIs, restock report, sales trend); Next.js dashboard + products UI
- **M4 — AI insights** ✅ LLM narration of deterministic analytics behind AI_ENABLED flag;
  CSV products import (upsert by SKU) + products/sales export
- **M5 — Hardening** ✅ JWT auth (admin/staff) protecting all business routes, audit log,
  Alembic migrations, docker-compose deploy with Postgres 16 (see DEPLOY.md)

## Open Questions (answer anytime, defaults chosen)

- Shop profile: assumed small shop, tens-to-hundreds of SKUs, single location
- Sales entry: manual/CSV first; POS integration deferred to post-M5
- Users: owner-only at first (no auth until M5)
- AI: optional paid API key behind feature flag

## Process

All decisions and their rationale are logged in `docs/DECISIONS.md` (ADR-lite);
every code change is recorded in `docs/CHANGELOG.md`. Both are updated whenever scope shifts or code changes.
