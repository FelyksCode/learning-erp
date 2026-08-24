# Decision Log (ADR-lite)

Every significant decision made while building this ERP: what we chose, why, and what we rejected.
Newest entries at the bottom. Format follows lightweight Architecture Decision Records.

---

## D-001 — Build custom ERP instead of deploying Odoo

**Date:** 2026-08-24
**Status:** Accepted

**Decision:** Build our own inventory ERP, using Odoo as a domain-model reference only.

**Why:** The primary goal is learning how an ERP works internally. Odoo would deliver working software
fast, but we would only configure it, not understand it. Custom build gives full control over the
analytics dashboard and AI restock insights that motivated the project.

**Rejected alternatives:**
- *Deploy Odoo (self-host)* — fastest path to working software + native POS integration, but zero
  learning value and heavy ops burden (Postgres + workers); revisit if shop needs POS integration urgently.
- *Django admin* — instant CRUD screens, but dated UI and less relevant to user's skill set.
- *Next.js fullstack + Supabase* — fast to ship, but less control over forecasting/domain logic.

## D-002 — Backend stack: FastAPI + SQLAlchemy 2 + Pydantic v2

**Date:** 2026-08-24
**Status:** Accepted

**Decision:** FastAPI with SQLAlchemy 2.x ORM (`Mapped`/`mapped_column` style) and Pydantic v2 schemas.
Python 3.12.

**Why:** Matches installed skills; typed end-to-end (Pydantic → SQLAlchemy); async-ready if needed;
interactive Swagger docs for free during development.

**Consequences:** CRUD wiring is manual (no Django-admin equivalent). Acceptable — writing routers is
part of the learning.

## D-003 — SQLite first, PostgreSQL-ready

**Date:** 2026-08-24
**Status:** Accepted

**Decision:** Default `DATABASE_URL = sqlite:///./erp.db`; any Postgres URL via env var switches over
with no code change. Schema created via `Base.metadata.create_all` on startup for now.

**Why:** Zero-setup local dev and instant smoke tests; the domain model is plain SQLAlchemy so the DB
is swappable.

**Consequences / deferred work:** Alembic migrations deferred until M5 (or when switching to Postgres);
SQLite's Numeric handling is approximate — fine while single-user dev. Tracked as TODO in PLAN.md M5.

## D-004 — Stock ledger: every quantity change is a StockMove row

**Date:** 2026-08-24
**Status:** Accepted

**Decision:** No stored "current quantity" column on products. On-hand is always **computed** as
`SUM(into INTERNAL locations) - SUM(out of INTERNAL locations)` per product
(`inventory_service.on_hand_for_product`).

**Why:** This is Odoo's core lesson — a movement ledger gives a complete audit trail (who moved what,
when, at what cost, why via reference) for free, and on-hand can never drift out of sync with history.

**Rejected alternative:** `products.quantity` column updated by endpoints — simpler queries, but no
audit trail and a classic source of ERP bugs.

**Consequences:** Listing N products runs one aggregate query each (N+1). Fine at shop scale (<1000 SKUs);
optimize with a single GROUP BY or SQL view later if needed.

## D-005 — Location-based moves instead of move-type flags

**Date:** 2026-08-24
**Status:** Accepted

**Decision:** A move has `from_location_id` → `to_location_id`, both always set. Locations are typed:
INTERNAL (SHOP, STORAGE), SUPPLIER, CUSTOMER, LOSS. Allowed transitions are an explicit allowlist:

```
SUPPLIER→INTERNAL   CUSTOMER→INTERNAL   LOSS→INTERNAL      (receiving / returns / recovery)
INTERNAL→CUSTOMER   INTERNAL→LOSS       INTERNAL→INTERNAL  (sales / shrinkage / transfers)
```

**Why:** Mirrors Odoo's two-location model. One mechanism covers purchases, sales, adjustments, damage,
and shop↔storage transfers — no special-case "adjust stock" endpoint that bypasses the audit trail.

## D-006 — Move shorthand defaults (ergonomics)

**Date:** 2026-08-24
**Status:** Accepted

**Decision:** In `POST /api/stock-moves`, omitting `to_location_code` means "sold to customer"
(destination = CUSTOMER); omitting `from_location_code` means "received from supplier" (source =
SUPPLIER). Supplying both codes handles transfers/losses explicitly.

**Why:** The 95% cases (buy stock, sell stock) become one-liners; unusual flows stay explicit.

## D-007 — unit_cost required on supplier receipts

**Date:** 2026-08-24
**Status:** Accepted

**Decision:** `POST /api/stock-moves` returns 400 when receiving from SUPPLIER without `unit_cost`.

**Why:** Captures purchase price at the moment of receipt, enabling COGS, valuation, and margin
analytics later without data backfill.

## D-008 — Soft-delete products

**Date:** 2026-08-24
**Status:** Accepted

**Decision:** `DELETE /api/products/{id}` sets `is_active=false` rather than removing rows.

**Why:** Products are referenced by immutable stock_moves; hard deletes would orphan history. Matches
Odoo's archive behavior.

## D-009 — Ruff lint profile for FastAPI

**Date:** 2026-08-24
**Status:** Accepted

**Decision:** Ruff with `line-length=100`, ignoring `B008` (function-call argument defaults — required
by FastAPI's `Depends()` idiom) and `FURB157` (`Decimal("0")` preferred over `Decimal(0)` for clarity).

**Why:** Standard FastAPI codebase config; everything else stays strict.

## D-010 — Documentation discipline

**Date:** 2026-08-24
**Status:** Accepted

**Decision:** Maintain `docs/DECISIONS.md` (this file) and `docs/CHANGELOG.md`. Every coding session
that changes code appends entries to both; PLAN.md is updated when scope shifts.

**Why:** User requirement — record every step, change, and decision so the project remains explainable.

## D-011 — Minimal PO lifecycle: draft → ordered → received (+ cancelled)

**Date:** 2026-08-24
**Status:** Accepted

**Decision:** Purchase orders have four states: `draft`, `ordered`, `received`, `cancelled`.
Transitions: draft→ordered (`POST /{id}/order`), ordered→received automatically when all lines fully
received, cancel allowed from draft/ordered only if nothing was received yet.

**Rejected alternative:** Odoo's full workflow (RFQ → approval → multi-step receiving → vendor bill).
Invoicing/bills are out of scope for this project; the extra states would add ceremony without
analytics value. Revisit if supplier invoice tracking is needed.

## D-012 — Receiving flows through the same stock-move ledger

**Date:** 2026-08-24
**Status:** Accepted

**Decision:** `POST /api/purchase-orders/{id}/receive` writes one `stock_moves` row per received line
(SUPPLIER → chosen internal location, default SHOP) with the PO line's `unit_cost` snapshot and a
`PO-{id}/{reference}` move reference. Partial receipts are allowed and tracked via
`purchase_order_lines.quantity_received`; over-receipt (qty > remaining) returns 400.

**Why:** Reusing the ledger keeps a single source of truth for on-hand (D-004) — no parallel "received
stock" pathway that could desync. Cost snapshot at receipt time feeds future COGS/valuation.

## D-013 — PO line cost defaults to product cost at creation time

**Date:** 2026-08-24
**Status:** Accepted

**Decision:** `POST /api/purchase-orders` line items omitting `unit_cost` inherit the product's current
`unit_cost`. The value is frozen into the line; later product cost edits do not affect existing POs.

**Why:** Convenient for quick ordering while preserving historical accuracy of what was actually agreed/paid.

## D-014 — Sales snapshot price at sale time; overselling blocked

**Date:** 2026-08-24
**Status:** Accepted

**Decision:** `POST /api/sales` lines omitting `unit_price` inherit the product's current `sale_price`,
frozen into the sale line (mirrors D-013). Each sale line checks computed on-hand and rejects the whole
sale with 400 if stock is insufficient ("no negative inventory").

**Rejected alternative:** Allow oversell like Odoo's configurable policy — for a single shop with a
physical shelf, selling more than on hand signals a data error, so hard-blocking keeps reports honest.

## D-015 — Analytics formulas (fixed window, deterministic)

**Date:** 2026-08-24
**Status:** Accepted

**Decision:**
- `avg_daily_sales` = total units sold in a **fixed trailing 30-day window ÷ 30** (not days-since-first-sale)
- `reorder_point = lead_time_days × avg_daily_sales + safety_stock`
- `suggested_order_qty = max(0, (lead_time_days + 7) × avg_daily_sales + safety_stock − on_hand)`
  (7-day review period)
- Status ladder: `out-of-stock` > `low` (on_hand ≤ reorder point) > `no-sales` (zero velocity) >
  `ok` > `not-tracked` (reorder disabled); report sorted by that priority then velocity
- Velocity counts only customer-bound sales (`sale_lines` joined to `sales`), not other outflows

**Why:** Deterministic math first; the AI layer (M4) will narrate these numbers rather than invent them.

## D-016 — Revenue analytics from sale-line price snapshots

**Date:** 2026-08-24
**Status:** Accepted

**Decision:** Revenue KPIs (`today/7d/30d`) and the trend chart aggregate
`Σ quantity × unit_price` from `sale_lines`, not from stock moves or current catalog prices.

**Why:** Prices change; historical revenue must not. Stock moves deliberately carry no revenue so the
ledger stays about quantity/cost only (single responsibility).

## D-017 — Frontend: Next.js client-side dashboard + npm allowScripts handling

**Date:** 2026-08-24
**Status:** Accepted

**Decision:**
- Next.js 16 + Tailwind v4 + Recharts; pages are client components fetching `/api/*` directly
  (`NEXT_PUBLIC_API_URL` override, default localhost:8000), keeping the frontend static-buildable
- Charts: one composed area chart (units left axis, revenue right axis)
- npm ≥11.16 gates install scripts; user's global `.npmrc` allowlist caused `EALLOWSCRIPTS` during
  scaffold. Fixed by declaring an `"allowScripts"` field in `frontend/package.json`
  (sharp, unrs-resolver, esbuild, @tailwindcss/oxide) — project-scoped, committed, reviewable

**Rejected alternative:** Server components proxying the API — adds runtime coupling during dev;
client fetch + CORS (already configured in M1) is simpler for a local tool.

## D-018 — AI layer is optional, deterministic-first, OpenAI-compatible

**Date:** 2026-08-24
**Status:** Accepted

**Decision:**
- Feature-flagged via settings: `AI_ENABLED` (default false), `AI_API_KEY`, `AI_BASE_URL`
  (default `https://api.openai.com/v1`, any OpenAI-compatible endpoint works), `AI_MODEL`
  (default gpt-4o-mini)
- The LLM only **narrates** the deterministic analytics (overview + restock report top 15 + 14-day
  trend, serialized to JSON with a strict system prompt); it never computes quantities itself
- `GET /api/ai/insights` returns 200 with `{enabled: false, reason}` when unconfigured (not an error),
  and 502 if the upstream LLM call fails

**Why:** The app must work fully without a paid key; hallucination risk is minimized by giving exact
numbers in context and forbidding invented figures in the prompt. OpenAI-compatible base URL keeps
provider choice open (local LLM servers included).

**Rejected alternatives:** Local forecasting library (statsmodels/prophet) — heavier deps; simple
heuristics already cover reorder math. LangChain — unnecessary abstraction for one HTTP call.

## D-019 — CSV import upserts by SKU; exports are plain stdlib csv

**Date:** 2026-08-24
**Status:** Accepted

**Decision:**
- `POST /api/import/products`: DictReader with case/space-insensitive headers (`sku`, `name`
  required; `category`, `unit_cost`, `sale_price` optional). Rows match existing products by SKU →
  update name/cost/price/category; otherwise create. Unknown categories are auto-created.
  Response reports created/updated/skipped counts.
- `GET /api/export/products.csv` includes live computed on-hand and 30d velocity;
  `GET /api/export/sales.csv` exports sale lines with snapshot prices and line revenue.

**Why:** Upsert-by-SKU makes re-import idempotent (safe to fix a file and upload again). stdlib csv
keeps zero extra dependencies; pandas would be overkill at shop scale.

## D-020 — httpx promoted to a runtime dependency

**Date:** 2026-08-24
**Status:** Accepted

**Decision:** `httpx` moved from dev extras to main dependencies (used by `ai_service`), and
`python-multipart` added (required by FastAPI's UploadFile).

**Why:** Both are needed in production paths now, not just tests.

## D-021 — Auth: pbkdf2 hashing + PyJWT tokens, two roles

**Date:** 2026-08-24
**Status:** Accepted

**Decision:** Passwords hashed with stdlib `hashlib.pbkdf2_hmac` (200k iterations, random salt,
constant-time compare). Tokens are HS256 JWTs via `pyjwt` carrying `sub/username/role/iat/exp`
(12h lifetime). Two roles: `admin` (user management, audit log) and `staff` (everything else).

**Rejected alternatives:** `passlib[bcrypt]` — extra dependency with occasional native-wheel friction
on Windows; stdlib pbkdf2 is adequate for a learning project. Hand-rolled HMAC tokens — reinventing
JWT badly; pyjwt is tiny and standard.

## D-022 — Global router protection instead of per-endpoint flags

**Date:** 2026-08-24
**Status:** Accepted

**Decision:** All business routers mounted with `dependencies=[Depends(get_current_user)]` in
`main.py`; only `/api/auth/*` and `/api/health` stay open. Admin-only endpoints additionally depend
on `require_admin`.

**Why:** One place to reason about exposure — new routers are protected by default when added to the
loop; forgetting protection is the classic auth bug.

## D-023 — Audit log design: explicit post-commit entries, admin-only reads

**Date:** 2026-08-24
**Status:** Accepted

**Decision:** Mutating endpoints call `audit(db, user, action, entity, entity_id, detail)` after their
commit; the helper stores username snapshot + JSON detail and commits itself. `GET /api/audit`
(admin-only) returns newest-first paginated rows. Audited today: product create/update/deactivate,
stock moves, PO create/order/receive/cancel, sales, CSV import, user management.
Password values are never stored in detail (masked as `"***"`).

**Why:** Explicit calls keep the ledger invariant clean (audit rows are not stock moves) while staying
grep-able. A middleware would capture nothing meaningful without endpoint context anyway.

## D-024 — Table creation policy: auto-create for dev, Alembic as source of truth

**Date:** 2026-08-24
**Status:** Accepted

**Decision:** Lifespan runs `Base.metadata.create_all` only when `AUTO_CREATE_TABLES=true`
(default true so dev/Docker-less SQLite "just works"). Alembic is initialized with an autogenerated
initial revision covering all tables; production/compose sets `AUTO_CREATE_TABLES=false` and runs
`alembic upgrade head`. env.py reads the URL from app settings and enables `render_as_batch` on
SQLite (required for future ALTER support).

**Why:** Zero-setup first run vs. migration discipline where it matters; documented tradeoff.

## D-025 — Seeded admin/admin with explicit warning

**Date:** 2026-08-24
**Status:** Accepted

**Decision:** Fresh databases get one user `admin/admin` (role admin). The login page shows the
default in an amber notice; DEPLOY.md instructs changing it immediately and setting a real
`JWT_SECRET` (dev default is public in this repo).

**Why:** Bootstrapping needs a known credential; hiding it silently would lock out fresh installs.

## D-026 — Deploy shape: docker-compose with Postgres + standalone Next.js

**Date:** 2026-08-24
**Status:** Accepted

**Decision:** Root `docker-compose.yml`: postgres:16-alpine (+ healthcheck, named volume), backend
built from `backend/Dockerfile` (slim python, pip install ., uvicorn), frontend multi-stage build
using Next.js `output: "standalone"` with `NEXT_PUBLIC_API_URL` as a build arg. Backend gets
`postgresql+psycopg://…` (psycopg 3 added to deps).

**Why:** Compose is the simplest reproducible single-host deploy; standalone output shrinks the
frontend runtime image to node + server.js without node_modules.

## D-027 — Frontend visual identity: "The Stock Ledger" (shop-stationery system)

**Date:** 2026-08-24
**Status:** Accepted

**Decision:** Replace the default SaaS look with an identity drawn from shop paperwork
(bin cards, delivery notes, rubber stamps, label-printer SKUs):
- Palette (tokens in `globals.css @theme`): paper `#FCF9F0` surfaces on manila `#EDE3CD` field,
  kraft `#B9A67F` borders + rule `#E2D6BC` ledger lines, ink `#262119` text,
  **biro blue `#2D4FA1`** for actions/links/revenue, **stamp red `#BF3B2B` reserved exclusively for
  alerts**, pencil `#6E6555` meta. Semantic green removed entirely.
- Type: Barlow Semi Condensed (uppercase tracked display/headers), IBM Plex Sans (body),
  IBM Plex Mono for every numeral/SKU/date (tabular data reads like label-printer output).
- Signature element: statuses rendered as **rubber stamps** ("ORDER NOW", "REORDER", "IN COVER",
  "NOT MOVING") with deterministic tilt and a staggered stamp-in animation on load;
  suggested order quantities circled like a pen annotation. Folder-tab navigation, delivery-note
  masthead, underline-style form inputs, graph-paper chart grid.
- Quality floor kept: focus-visible rings (biro), prefers-reduced-motion disables stamping,
  responsive to mobile (strip collapses to 2 columns, tables scroll).

**Rejected alternatives:** warm-cream + serif display + terracotta (AI-default look #1); dark UI +
acid accent (#2) — wrong ergonomics for a daily daylight tool; keeping white/emerald SaaS style —
exactly the templated result the brief rejects. Green removal risk justified: urgency is encoded by
the stamp's word/border/tilt, so red-only still communicates instantly while making the palette ours.

Copy rules applied alongside: plain verbs (Add product / Receive / Sell), status words that name the
action (ORDER NOW, not "critical"), empty states that direct (add items / import CSV), errors state
cause + fix without apologizing.

## D-028 — Rendering strategy: server components read, client components mutate

**Date:** 2026-08-24
**Status:** Accepted

**Decision:** Dashboard and Products pages are now async Server Components fetching the FastAPI API
at request time (`cache: "no-store"` — ops data must be fresh) via `lib/api-server.ts`, which reads
the session token from cookies and redirects to /login on 401. Interactive leaves stay client
components: `AdvisorNote` (regenerate), `ProductForm`, `ProductActions`, `ProductToolbar`
(mutations POST from the browser then `router.refresh()` to re-run the server fetch).
Session moved from **localStorage to a `erp_token` cookie** (path=/, 7d, SameSite=Lax, readable by
JS) so both rendering contexts share one credential. Every route segment gained `loading.tsx`
(skeletons) and `error.tsx` boundaries per Next.js requirements; `/login` remains fully client.

**Why:** Server-rendered first paint carries real data (no spinner-then-content waterfall); client
boundary is pushed to exactly where interactivity lives. Cookie over localStorage was required to let
server components attach the bearer header; non-httpOnly is a conscious tradeoff for a local tool
(XSS surface accepted, documented here).

**Rejected alternatives:** Full client-side app (previous state — violated RSC-first and shipped no
boundaries); httpOnly cookie + route-handler proxy for every mutation (more moving parts than value
here); SWR/React Query layer (unnecessary once reads are server-side and mutations refresh the router).

## D-029 — Test architecture: layered pytest suite with isolated in-memory database

**Date:** 2026-08-24
**Status:** Accepted

**Decision:** `backend/tests/` is a proper pytest suite layered by scope, marked via
`[tool.pytest.ini_options]` markers (`unit` / `api` / `integration`), separate from the retained
end-to-end `smoke_test*.py` scripts:
- **Unit** (`tests/unit/`): pure service/security logic against a direct ORM session — password
  hashing, JWT claims/tampering, on-hand math, move-direction allowlist, velocity/reorder formulas.
- **API** (`tests/api/`): endpoints through `TestClient` — auth guards (anonymous/garbage/staff),
  audit trail contents+ordering, CSV export→import roundtrip.
- **Integration** (`tests/api/test_lifecycle.py`): multi-step flows — PO order→receive guardrails,
  sell-below-zero rejection, price-snapshot durability.

Key mechanisms: a single **in-memory SQLite engine** (`StaticPool`) injected via FastAPI's
`app.dependency_overrides[get_db]`, with an autouse function-scoped `fresh_database` fixture that
drops/recreates/seeds before *every* test — total isolation, no ordering dependence. Fixtures
compose (`raw_client → client → staff_client`) plus a `make_product` factory fixture.
Coverage measured with pytest-cov (suite reaches ~87% of app/; gaps are routers exercised only by
smoke scripts).

**Why:** The smoke scripts proved features but taught nothing about structure and couldn't run one
test in isolation. Layered pytest gives fast failure localization (unit fails = logic bug; API fails =
wiring bug) and is the industry shape QA grows on.

**Rejected alternatives:** File-based test DB (slower, cleanup hazards); transaction-rollback-per-test
(savepoints interact badly with our commit-inside-service design); deleting smoke scripts (kept as
whole-system regression checks).






