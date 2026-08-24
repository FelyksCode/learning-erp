# Learning ERP

Custom inventory ERP for a small shop, built for learning — domain model inspired by
[Odoo](https://www.odoo.com) (locations + stock moves), simplified to what one shop needs.
See [PLAN.md](PLAN.md) for architecture, domain mapping, and milestones.

## Documentation

- [docs/DECISIONS.md](docs/DECISIONS.md) — every decision, its reasoning, and rejected alternatives (ADR-lite)
- [docs/CHANGELOG.md](docs/CHANGELOG.md) — dated log of all changes per milestone

## Stack

- **Backend**: FastAPI + SQLAlchemy 2 + Pydantic v2 (Python 3.12)
- **DB**: SQLite by default (`DATABASE_URL` env var switches to PostgreSQL)
- **Frontend**: Next.js 16 + Tailwind v4 + Recharts

## Quickstart

**Backend** (API on http://localhost:8000, Swagger docs at `/docs`):

```bash
cd backend
python -m venv .venv
.venv\Scripts\pip install -e ".[dev]"
.venv\Scripts\uvicorn app.main:app --reload
```

Optional demo data — resets the DB with 7 products and 27 days of sales history:

```bash
.venv\Scripts\python seed_demo.py
```

**Frontend** (dashboard on http://localhost:3000):

```bash
cd frontend
npm install
npm run dev
```

Set `NEXT_PUBLIC_API_URL` to point the UI at a different API host.

**Login**: every fresh database seeds **admin / admin** — change the password immediately
(all business endpoints require a bearer token; only health and login are open).
Deployment via Docker Compose (Postgres 16 + both images): see [DEPLOY.md](DEPLOY.md).

## Core concepts

- Every quantity change is a **stock move** (`from_location -> to_location`) — on-hand stock is always
  computed from moves, never stored twice (Odoo-style audit trail)
- Seeded locations: `SUPPLIER`, `SHOP`, `STORAGE`, `CUSTOMER`, `LOSS`
- Move shorthand: omit `to_location_code` → sale to customer; omit `from_location_code` → receiving from supplier
  (requires `unit_cost`)
- Valid directions only (e.g. `SUPPLIER -> SHOP`, `SHOP -> CUSTOMER`, `SHOP -> LOSS`); the API rejects nonsense

## API v1 (mounted under `/api`)

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/auth/token` | Login (OAuth2 form) → JWT bearer |
| GET | `/api/auth/me` | Current user |
| GET/POST/PATCH | `/api/auth/users` | User management (admin-only) |
| GET | `/api/audit` | Audit trail (admin-only, paginated) |
| GET/POST | `/api/products` | List (search `q`, filter `category_id`) / create |
| GET/PATCH/DELETE | `/api/products/{id}` | Detail incl. live `on_hand` / update / deactivate |
| GET/POST | `/api/catalog/categories` | Product categories |
| GET/POST | `/api/catalog/partners` | Suppliers & customers (`?partner_type=`) |
| GET/POST | `/api/stock-moves` | Movement ledger / post a move |
| GET/POST | `/api/purchase-orders` | List (`?status=`) / create draft PO |
| GET | `/api/purchase-orders/{id}` | Detail incl. lines + total_cost |
| POST | `/api/purchase-orders/{id}/order` | draft → ordered |
| POST | `/api/purchase-orders/{id}/receive` | Receive lines → auto stock moves (partial ok, no over-receipt) |
| POST | `/api/purchase-orders/{id}/cancel` | Cancel if nothing received yet |
| GET/POST | `/api/sales` | List (`?product_id=`) / record sale (auto stock moves, price snapshot, oversell blocked) |
| GET | `/api/analytics/overview` | KPIs: SKUs, stock value, low-stock count, revenue today/7d/30d |
| GET | `/api/analytics/restock` | Reorder report: velocity, days-of-cover, reorder point, suggested qty, status |
| GET | `/api/analytics/sales-trend` | Daily qty/revenue buckets (`?days=&product_id=`) for charts |
| GET | `/api/analytics/velocity/{id}` | Avg daily sales per product over a window |
| GET | `/api/ai/insights` | LLM restock advice (needs `AI_ENABLED` + `AI_API_KEY`; graceful hint otherwise) |
| GET | `/api/export/products.csv` / `/api/export/sales.csv` | CSV downloads |
| POST | `/api/import/products` | CSV upload, upsert by SKU (auto-creates categories) |
| GET | `/api/health` | Liveness |

### AI configuration (backend/.env)

| Variable | Default | Purpose |
|----------|---------|---------|
| `AI_ENABLED` | `false` | Master switch for `/api/ai/insights` |
| `AI_API_KEY` | — | API key for any OpenAI-compatible provider |
| `AI_BASE_URL` | `https://api.openai.com/v1` | Provider endpoint |
| `AI_MODEL` | `gpt-4o-mini` | Chat model used |

The AI only narrates the deterministic analytics (restock report, trend) — it never invents quantities.

## Smoke tests

```bash
cd backend
.venv\Scripts\python smoke_test.py      # M1: inventory core
.venv\Scripts\python smoke_test_m2.py   # M2: purchasing lifecycle
.venv\Scripts\python smoke_test_m3.py   # M3: sales + analytics math
.venv\Scripts\python smoke_test_m4.py   # M4: AI flag + CSV roundtrip
.venv\Scripts\python smoke_test_m5.py   # M5: auth, roles, audit trail
```

## Milestones

- [x] **M1** Core inventory: products, categories, partners, locations, stock moves, on-hand
- [x] **M2** Purchasing: purchase orders (draft→ordered→received), receiving writes ledger moves
- [x] **M3** Sales + Next.js dashboard (velocity, days-of-cover, reorder points)
- [x] **M4** AI insights (LLM restock recommendations behind feature flag), CSV import/export
- [x] **M5** Auth/roles (JWT), audit log, Alembic migrations, Docker Compose deploy
