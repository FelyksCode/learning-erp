# AGENTS.md

Guidance for coding agents working in this repo. Read this before making changes.

## What this project is

A custom **inventory ERP for a small shop**, built as a learning project. The domain model mirrors
Odoo's proven concepts (typed locations, immutable stock-move ledger) but implements only what one
shop needs. Goal features: stock tracking, restock analytics (velocity/days-of-cover/reorder points),
and LLM-generated restock advice.

## Non-negotiable conventions

1. **Documentation discipline** (user requirement): every coding session that changes code MUST append
   entries to `docs/CHANGELOG.md` and record any non-obvious choice in `docs/DECISIONS.md` (ADR-lite,
   numbered D-001…D-0xx). Update `PLAN.md` when scope shifts.
2. **Stock ledger invariant**: every quantity change must be a `stock_moves` row. On-hand is always
   *computed* (`inventory_service.on_hand_for_product`), never stored on the product. No endpoint may
   bypass this by editing a qty field.
3. **Audit trail**: user-facing mutations call `audit(db, current_user, action, entity, id, detail)`
   after committing (see existing routers for the pattern).
4. **Snapshots over references**: PO lines freeze `unit_cost`, sale lines freeze `unit_price`.
   Revenue analytics use sale-line snapshots, never current catalog prices.
5. **No comments in code** unless functional (e.g. targeted `# noqa` with reason).
6. Ruff must stay clean: `cd backend && .venv\Scripts\ruff check app`
   (ignored rules live in `pyproject.toml`: B008 FastAPI Depends idiom, FURB157).
7. Windows environment: shell is cmd.exe — no heredocs (`<<`), no `tail`; use `findstr`,
   `python -c "..."` or script files instead.

## Stack & layout

```
backend/    FastAPI + SQLAlchemy 2 (sync) + Pydantic v2, Python 3.12, SQLite default (DATABASE_URL switches to Postgres)
  app/models/        domain tables (Product, StockMove, PurchaseOrder, Sale, Partner, Location, User, AuditLog…)
  app/schemas/       Pydantic request/response models
  app/api/routers/   inventory, stock_moves, purchasing, sales(+analytics), ai, data_io, auth, audit
  app/api/deps.py    get_current_user / require_admin (JWT bearer)
  app/services/      business logic (inventory_service, sales_service, purchasing_service, ai_service, audit_service)
  app/core/          config (env via pydantic-settings), db engine/session, security (pbkdf2 + pyjwt)
  alembic/           migrations (initial revision d79a55b5a3b5 covers all tables)
  Dockerfile         python:3.12-slim, uvicorn entrypoint
frontend/   Next.js 16 App Router + Tailwind v4 (@theme tokens) + Recharts — visual identity: "The Stock Ledger"
  src/app/           routes are async SERVER components (no-store fetches); loading.tsx + error.tsx per segment
  src/components/    client leaves only: NavTabs, UserMenu, MastheadMeta, AdvisorNote, SalesChart, ProductPanels
  src/lib/api.ts     browser helpers (cookie token, JSON post/get)
  src/lib/api-server.ts  server fetcher (cookies() → bearer, 401 → redirect /login)
  Dockerfile         multi-stage, standalone output
docker-compose.yml   postgres:16 + backend + frontend (AUTO_CREATE_TABLES=false, run alembic upgrade head once)
DEPLOY.md            env var reference, first-login checklist
docs/                DECISIONS.md (ADR-lite, D-001…D-028) + CHANGELOG.md (dated log)
PLAN.md              architecture, Odoo→ours mapping, reorder math formulas, milestones
```

## Commands

```bash
# backend
cd backend
python -m venv .venv                       # first time only
.venv\Scripts\pip install -e ".[dev]"
.venv\Scripts\uvicorn app.main:app --reload          # → http://localhost:8000/docs

.venv\Scripts\python seed_demo.py          # reset DB w/ demo data (7 products, 27 days of sales)

# tests (each resets expectations against a fresh DB; delete erp.db between runs if needed)
.venv\Scripts\python smoke_test.py         # M1 inventory core
.venv\Scripts\python smoke_test_m2.py      # M2 purchase lifecycle
.venv\Scripts\python smoke_test_m3.py      # M3 sales + analytics math
.venv\Scripts\python smoke_test_m4.py      # M4 AI flag + CSV roundtrip
.venv\Scripts\python smoke_test_m5.py      # M5 auth, roles, audit trail

# pytest suite (isolated in-memory DB; see tests/conftest.py + DECISIONS D-029)
.venv\Scripts\python -m pytest -v                    # whole suite
.venv\Scripts\python -m pytest -m unit -v            # only unit layer
.venv\Scripts\python -m pytest --cov=app             # with coverage

# migrations (schema changes: edit models → autogenerate → review → upgrade)
.venv\Scripts\alembic revision --autogenerate -m "describe change"
.venv\Scripts\alembic upgrade head

# deploy
docker compose up --build                  # postgres + backend + frontend (see DEPLOY.md)
python verify_containers.py                # E2E check against the live stack (stack must be up)
docker compose down                        # stop; -v also wipes the pgdata volume

# frontend
cd frontend && npm install && npm run dev            # → http://localhost:3000
npm run build                              # verify production build after UI changes
```

## Gotchas learned the hard way (don't rediscover these)

- Joined collection eager loads (`PurchaseOrder.lines`, lazy="joined") need `.unique()` before
  `.all()` on Results.
- Pydantic v2 serializes `Decimal` fields to JSON **strings** ("63.00") — compare accordingly in tests.
- npm ≥11.16 gates install scripts: `allowScripts` field lives in `frontend/package.json`
  (global ~/.npmrc allowlist caused EALLOWSCRIPTS during scaffold).
- FastAPI `UploadFile` needs `python-multipart` installed.
- Seeding: never read `.id` of a just-added ORM object without flush — use relationship objects.
- Default seeded locations: SUPPLIER/SHOP/STORAGE/CUSTOMER/LOSS. Move shorthand: omitting one side
  means SUPPLIER source (needs unit_cost) or CUSTOMER destination.
- Reorder math (fixed 30d window ÷30): `reorder_point = lead_time_days × avg_daily_sales +
  safety_stock`; suggested order covers lead+7d. AI layer only narrates these numbers.
- Frontend session lives in the `erp_token` **cookie** (not localStorage) so Server Components can
  attach it server-side (`lib/api-server.ts` reads it via `cookies()`). Don't reintroduce
  localStorage — login would silently stop working for RSC pages.
- Recharts components must stay in `"use client"` files; dashboard/products pages are async Server
  Components (`no-store` fetches), mutations are client leaves + `router.refresh()`.
- Tailwind v4 design tokens live in `globals.css` `@theme` (colors) + `@theme inline` (fonts —
  must be inline because they reference next/font runtime vars). Use the named classes
  (bg-paper, text-ink, border-kraft…) instead of raw hexes.
- Keep `loading.tsx`/`error.tsx` in both route segments; error copy states cause + fix.
- In Docker the backend container migrates BEFORE uvicorn starts (`alembic upgrade head` in CMD);
  seeding is guarded on table existence. With `AUTO_CREATE_TABLES=false` never assume tables exist
  at import/lifespan time — that's what crashed the first real boot (fixed 2026-08-24).
- `.dockerignore` files are load-bearing: frontend context is ~1.6KB because node_modules/.next are
  excluded — don't delete them or builds ship 568MB to the daemon.

## Current status (session recap)

**ALL MILESTONES M1–M5 COMPLETE** (2026-08-24), followed by three post-M5 hardening/polish passes:
1. FastAPI standards review — fixed `/api/sales?product_id=` filter-after-limit bug, overview N+1
2. Visual identity "The Stock Ledger" (D-027) — shop-stationery design system, stamp statuses,
   biro/stamp palette, no green
3. App Router architecture pass (D-028) — dashboard/products are async server components with
   cookie session, client mutation leaves + router.refresh(), loading/error boundaries per segment

The app is feature-complete for a single shop: inventory ledger, purchasing, sales + analytics
dashboard, AI insights (flagged), CSV I/O, JWT auth with admin/staff roles + audit trail, Alembic
migrations, Docker Compose deploy. Default logins after any fresh DB: **admin / admin**
(change-me warning documented in DEPLOY.md and shown on the login page).

Verification state at handoff: all five smoke suites pass (run them after deleting `backend/erp.db`),
`ruff check app` clean, `npm run build` clean. Alembic initial revision verified against an empty DB.

Possible next steps (not started):
- Change-default-password flow / password change UI for staff users
- Suppliers/PO UI screens (backend exists; frontend only has products + dashboard)
- Sales history page; per-product analytics drill-down
- Postgres-specific perf work (indexes on stock_moves.moved_at) if data grows
