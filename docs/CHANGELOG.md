# Changelog

Dated record of every change. Newest first within each release/milestone.
Format: `### YYYY-MM-DD — short title` with bullet points per change.

---

## [Post-M5] QA test suite — 2026-08-24

Introduced a layered pytest suite for learning + regression (rationale: DECISIONS D-029).

### Test infrastructure
- `tests/conftest.py`: in-memory SQLite engine (StaticPool) injected via
  `app.dependency_overrides[get_db]`; autouse `fresh_database` fixture drops/creates/seeds schema
  before every test (full isolation); composed fixtures `raw_client` / `client` (admin) /
  `staff_client`, plus `make_product` factory and direct-ORM `db_session`.
- `pyproject.toml`: pytest config (testpaths, markers unit/api/integration); dev dep + pytest-cov.
- Removed stale `tests/__init__.py`.

### Tests added (30 total, all green)
- `unit/test_security.py` — hash/verify roundtrip + salting, JWT claims + tamper rejection,
  plaintext never stored.
- `unit/test_inventory_logic.py` — on-hand zero/in-out/transfer-neutral math; move-direction
  allowlist + shorthand defaults; velocity = qty ÷ full window; reorder-point & suggested-qty
  formulas; status ladder (low / not-tracked).
- `api/test_auth_flow.py` — health open vs business routes 401, garbage token, wrong password,
  /me identity, staff 403 on users/audit but allowed day-job ops, duplicate username 409,
  deactivated login block.
- `api/test_lifecycle.py` — PO receive-before-order guard, order→receive→sell happy path with
  analytics tie-in, over-receipt rejection, insufficient-stock rejection, price snapshot survives
  later edits.
- `api/test_audit_and_data_io.py` — audit entries per mutation incl. newest-first ordering,
  CSV export header/rows → re-import upsert roundtrip, non-CSV rejection.

### Verification
- `pytest tests -v` → **30 passed** (~7s, fully isolated).
- `pytest --cov=app` → **87%** coverage of app/ (uncovered lines are routers covered by the retained
  smoke scripts). All smoke_test*.py still pass unchanged.

---

## [Post-M5] Next.js App Router architecture pass — 2026-08-24

Applied the nextjs-developer skill: fixed RSC/client boundary + missing route boundaries
(rationale: DECISIONS D-028). Visual design unchanged.

### Architecture
- Session moved localStorage → `erp_token` cookie (path=/, max-age 7d, SameSite=Lax) so server
  components can attach the bearer header; `lib/api.ts` reads/writes/clears cookie, 401 handler
  unchanged for client mutations; login page uses `setToken()`.
- New `lib/api-server.ts`: `apiGet<T>()` — server fetch with cookie-derived Authorization,
  `cache: "no-store"`, redirect to /login on 401, error detail propagation.
- Dashboard (`app/page.tsx`) and Products (`app/products/page.tsx`) rewritten as async Server
  Components fetching overview/restock/trend/products at request time via Promise.all.
- Client leaves extracted: `components/AdvisorNote.tsx` (AI regenerate), `components/SalesChart.tsx`
  (Recharts must run client-side), `components/ProductPanels.tsx` (ProductForm / ProductActions /
  ProductToolbar using `router.refresh()` after POSTs to re-run the server render).

### Route boundaries (skill MUST-DO)
- `app/loading.tsx` + `app/error.tsx` (dashboard skeleton + "books won't open" retry panel)
- `app/products/loading.tsx` + `app/products/error.tsx`

### Verification
- `next build` clean; routes now `/login` static ○, `/products` dynamic ƒ (server-rendered per
  request as intended). Login→cookie flow verified by code path review; runtime smoke = start both
  servers and log in.

---

## [Post-M5] Frontend visual identity — "The Stock Ledger" — 2026-08-24

Design-lead pass replacing the generic white/emerald SaaS look (rationale + tokens: DECISIONS D-027).
No functional changes — same pages, same API calls.

### Design system
- `globals.css`: Tailwind v4 `@theme` tokens (paper/manila/kraft/rule/ink/biro/stamp/pencil),
  display+body+mono font vars, component classes (`.eyebrow`, `.doc-panel`, `.stamp`,
  `.ledger-input`), reduced-motion-gated stamp-in keyframes.
- Fonts via next/font/google: Barlow Semi Condensed (display), IBM Plex Sans (body),
  IBM Plex Mono (all numerals/SKUs/dates).

### Layout & components
- Masthead header: delivery-note style title block ("The Stock Ledger" + mono tagline), date meta
  (client-rendered to avoid hydration mismatch), thick ink rule; nav is now **folder tabs**
  (`components/NavTabs.tsx`, usePathname active state) overlapping the masthead rule.
- New `MastheadMeta.tsx` date stamp.
- Dashboard reordered for the owner's daily flow: counter strip → restock list → advisor's note →
  sales chart. KPIs are one ruled strip (divide-x), not five separate cards.
- Restock list: statuses are rubber stamps with human words (ORDER NOW / REORDER / IN COVER /
  NOT MOVING / —), deterministic tilts, staggered load animation; urgent rows tinted;
  suggested order qty circled biro-style; formula footnote in mono caps.
- Chart restyled to graph paper (dotted kraft grid, ink units area, biro revenue line,
  paper tooltip, mono ticks).
- Advisor note: left biro rule panel, "Write it again" regenerate action, directional empty text.
- Products page: "Product book" title row w/ Export/Import as ink-outline mono buttons;
  intake form as a document (underline inputs, mono numerics right-aligned); ledger table with
  Receive/Sell actions (outline vs solid biro); zero-on-hand rows tinted red.
- Login: centered stock-card panel with heavy top rule, underline inputs,
  "Open the book" submit, default-credential note in mono footer.

### Copy pass
Plain verbs everywhere (Add product / Receive / Sell / Write it again); errors state cause + fix
("Can't reach the API… Start the backend on localhost:8000, then reload"); empty states direct to
the action that fills them.

### Verification
- `npm run build` clean (routes /, /products, /login). Accessibility floor: focus-visible biro rings,
  prefers-reduced-motion respected, responsive (2-col strip on mobile, scrollable tables).

---

## [Post-M5] FastAPI standards review — 2026-08-24

Applied the fastapi-python skill as an audit pass over the backend. Conformance already high
(lifespan ✅, typed routes/response models ✅, DI via Depends ✅, guard clauses ✅, consistent
HTTPException mapping 400/401/403/404/409/502 ✅). Sync SQLAlchemy retained per D-002 — FastAPI
executes sync handlers in its threadpool, so DB blocking is contained; async migration would be a
stack change, not a refactor.

### Fixes
- `GET /api/sales?product_id=` filtered in Python *after* the SQL limit — matching sales older than
  the newest N were silently dropped when filtering. Now joins `sale_lines` and filters in SQL
  before limiting (also removes per-sale line scan).
- `/api/analytics/overview` re-fetched each Product inside the restock loop for unit_cost (N+1);
  now one id→cost map query.

### Verification
- Targeted check: 2 sales on one product both returned under filter; stock value unchanged.
- All five smoke suites green from fresh DB; `ruff check app` clean.

---

## [M5] Hardening — 2026-08-24

### Auth
- `models/user.py`: `users` (unique username, pbkdf2 password hash, admin/staff role, is_active).
- `core/security.py`: `hash_password`/`verify_password` (pbkdf2_hmac 200k iters, salted,
  constant-time compare), JWT create/decode (HS256, sub+username+role+exp).
- `core/config.py`: `jwt_secret`, `jwt_expire_minutes` (720), `auto_create_tables` (true).
- `api/deps.py`: `get_current_user` (Bearer token → User, 401 on missing/invalid/inactive),
  `require_admin` (403 otherwise).
- `api/routers/auth.py`: POST `/api/auth/token` (OAuth2 form login), GET `/me`,
  users CRUD (admin-only; create returns 409 on duplicate username; password never echoed;
  deactivation blocks login).
- `main.py`: all business routers mounted behind global auth dependency; only `/api/auth/*` and
  `/api/health` open. Lifespan seeds locations + default **admin/admin**.
- `pyproject.toml`: + pyjwt.

### Audit trail
- `models/audit_log.py`: user_id FK, username snapshot, action/entity indexed, entity_id, JSON detail.
- `services/audit_service.py`: `audit()` helper (post-commit, self-committing).
- Wired into: product create/update/deactivate, stock moves (from/to/qty/reference detail),
  PO create/order/receive/cancel, sale create, CSV import, user create/update (password masked "***").
- `api/routers/audit.py`: GET `/api/audit` admin-only, paginated (?entity= filter, total count).

### Migrations
- Alembic initialized (`backend/alembic/`, env.py reads DATABASE_URL from settings,
  render_as_batch for SQLite); autogenerated initial revision `d79a55b5a3b5_initial_schema`
  covering all 11 tables; verified fresh `upgrade head` from empty DB.
- Table auto-creation gated by `AUTO_CREATE_TABLES` (default true).

### Deploy
- `backend/Dockerfile` (python:3.12-slim), `frontend/Dockerfile` (multi-stage, standalone output),
  `next.config.ts`: `output: "standalone"`.
- Root `docker-compose.yml`: postgres:16-alpine + backend (DATABASE_URL=postgresql+psycopg://…,
  AUTO_CREATE_TABLES=false) + frontend; `DEPLOY.md` with env var reference and first-login checklist.
- `pyproject.toml`: + psycopg[binary].

### Frontend
- `/login` page: form-urlencoded token post, localStorage storage, error display, default-credential notice.
- `lib/api.ts`: token helpers; Authorization header on all calls; 401 → clear token + redirect /login.
- Header `UserMenu`: identity via /auth/me, role badge, logout button.

### Fixes during build
- Default dev JWT secret was <32 bytes → pyjwt InsecureKeyLengthWarning; lengthened dev default,
  production override documented.
- Audit initially empty in m5 test because no audited mutation had run — added product lifecycle +
  user events to the test; also wired audit into user management (security-relevant).

### Verification
- New `smoke_test_m5.py` — **20/20 PASS**: health open, unauthenticated 401, wrong password 401,
  admin flow, /me, staff role guards (403 users/audit, allowed business ops), audit rows with correct
  usernames/actions, deactivated-user login block, garbage-token rejection.
- smoke_test*.py M1–M4 retrofitted with a shared `login(c)` helper (script-file patcher, cmd.exe-safe);
  all suites re-verified green after protection was enabled.
- Alembic fresh-database upgrade verified (all tables present). `ruff check app` clean.
- `npm run build` clean incl. new /login route.

---

## [M4] AI insights + CSV — 2026-08-24

### Backend — AI
- `core/config.py`: added `ai_enabled` (default False), `ai_api_key`, `ai_base_url`
  (OpenAI-compatible), `ai_model`.
- `services/ai_service.py`: `build_context()` serializes overview + top-15 restock rows + 14d trend;
  `generate_insight()` posts chat/completions via httpx with a strict analyst system prompt
  (use only provided numbers, bullets, ≤150 words); `AIError` for missing key / HTTP failure /
  unexpected response shape.
- `api/routers/ai.py`: `GET /api/ai/insights` → 200 `{enabled:false, reason}` when unconfigured,
  insight text when enabled, 502 on upstream failure.

### Backend — CSV
- `api/routers/data_io.py`:
  - `GET /api/export/products.csv` (live on_hand + avg_daily_sales_30d columns)
  - `GET /api/export/sales.csv` (sale lines, snapshot prices, line revenue)
  - `POST /api/import/products` (multipart upload; case-insensitive headers; upsert by SKU;
    auto-create categories; created/updated/skipped counts; non-.csv rejected)
- `main.py`: registered ai + data_io routers.
- `pyproject.toml`: httpx → runtime dep; + python-multipart.

### Frontend
- Dashboard: "AI insights" card — violet accent when active, Regenerate button (POST), graceful
  setup hint when disabled (`reason` from API).
- Products page: Export CSV link + Import CSV file picker with result alert and error surfacing.
- `lib/api.ts`: `AIInsights` type.

### Fixes during build
- FastAPI UploadFile requires python-multipart at import time → added dependency.
- Test expectation bugs: Decimal fields serialize as strings (compare accordingly); sales export
  price correctly reflects the post-upsert snapshot (3×3.00=9.00), not the pre-upsert price.
- Ruff: UP017 autofix; targeted `# noqa: BLE001` on deliberate broad catch in import rollback path.

### Verification
- New `smoke_test_m4.py` — **11/11 PASS**: disabled-by-default hint, CSV create→upsert roundtrip,
  category auto-create, computed on-hand/velocity in products export, sales export w/ revenue,
  non-csv rejection. M1–M3 suites still green; `ruff check app` clean; `npm run build` clean.
- Live LLM call not exercised (needs real key) — covered by contract tests around it.

---

## [M3] Sales + Dashboard — 2026-08-24

### Backend — sales
- `models/sale.py`: `sales` (reference unique nullable, customer FK optional, sold_at, notes) +
  `sale_lines` (product FK, quantity, unit_price snapshot; joined product for display).
- `schemas/sales.py`: `SaleCreate`/`SaleOut` (+computed `total_revenue`), line in/out,
  `OverviewOut`, `RestockRow`, `TrendPoint`, `VelocityOut`.
- `services/sales_service.py`:
  - `create_sale` — validates customer type, defaults price from product, checks per-line on-hand
    (rejects whole sale if insufficient), picks the internal location holding the most stock as the
    move source, writes SHOP→CUSTOMER ledger moves with `SALE-{id}/{reference}`.
  - `avg_daily_sales` — fixed 30d window ÷ 30.
  - `restock_report` — per active product: on-hand, velocity, days-of-cover, reorder point,
    suggested order qty (lead+7d cover), status ladder, sorted by urgency.
  - `overview` — SKU count, stock value at cost, low/out-of-stock counts, revenue today/7d/30d.
  - `sales_trend` — daily qty+revenue buckets from sale lines, optional product filter.
- `api/routers/sales.py`: `/api/sales` GET (?product_id=)/POST;
  `/api/analytics/overview|restock|sales-trend|velocity/{id}` GET. Registered under `/api`.

### Frontend (new `frontend/`)
- Scaffolded Next.js 16 + TS + Tailwind v4 (`create-next-app`); added `recharts`.
- `src/lib/api.ts`: typed API client (`get`/`post`, `ApiError` with backend `detail`),
  base URL from `NEXT_PUBLIC_API_URL` (default localhost:8000/api).
- `src/app/layout.tsx`: app shell "SHOPERP" with nav (Dashboard, Products); minimal `globals.css`
  (single `@import "tailwindcss"`).
- `src/app/page.tsx`: dashboard — 5 KPI cards, 30-day sales composed area chart (units + revenue),
  restock recommendations table with status pills and formula footnote.
- `src/app/products/page.tsx`: product table (cost/price/on-hand) with create form and per-row
  Receive/Sell actions (prompt-based), error banner surfacing backend messages.
- `package.json`: added `"allowScripts"` field (sharp, unrs-resolver, esbuild, @tailwindcss/oxide).

### Environment fixes
- npm ≥11.16 install-script gating: scaffold install died with `EALLOWSCRIPTS` because the user's
  global `.npmrc` allowlist doesn't apply to project installs. Fixed via project `allowScripts`
  field (researched npm/cli#9783 + docs). eslint-visitor-keys EBADENGINE warning noted (node 22.11
  vs required 22.13+; warning only).

### Fixes during build
- Recharts v3 Tooltip formatter typing → widened to `(value, name)` with `Number()` coercion.
- seed_demo.py: wrong import path for `Base`; used unflushed `p.id` in PO lines → relationship refs.

### Verification
- New `smoke_test_m3.py` — **14/14 PASS**: PO receipt → sale flow, revenue math (7×1.20=8.40),
  price defaulting, on-hand 100−7=93, oversell rejected, velocity = 7/30 exactly,
  reorder point = lead×daily+safety exact match, suggested-qty formula, trend bucket appears on the
  backdated date, overview KPIs/revenue_30d correct. Backdating helper edits sold_at directly in SQLite.
- M1+M2 smoke tests still pass; `ruff check app` clean; `npm run build` compiles clean (static routes /).
- `seed_demo.py`: resets DB, seeds 7 products across 3 categories, initial PO received, 27 days of
  sales with weekend/growth variation → CHOC-90 and TISSUE-200 land near reorder point so the
  restock table shows actionable rows. On-hand all positive after scaling fix.
- Live uvicorn boot check skipped deliberately (Windows shell backgrounding friction); logic covered
  by TestClient suite. Run instructions documented in README instead.

---

## [M2] Purchasing — 2026-08-24

### Models
- `models/purchase_order.py`: `purchase_orders` (supplier FK, `PurchaseOrderStatus` enum
  draft/ordered/received/cancelled, unique optional reference, ordered_at/received_at) +
  `purchase_order_lines` (product FK, quantity, quantity_received default 0, unit_cost snapshot;
  joined product relationship for display).
- `models/__init__.py`: exported new models/status enum.

### Schemas
- `schemas/purchasing.py`: `POCreate` (supplier + 1..n lines; line unit_cost optional),
  `POLineIn/Out` (out includes product_sku/product_name via `from_line` helper), `POOut`
  (status as string, computed `total_cost = Σ qty × unit_cost`), `ReceiveIn` (destination
  location_code default SHOP; lines optional → receive-all-remaining), `ReceiveLineIn`.

### Services
- `services/purchasing_service.py` with domain errors as `PurchaseError` (translated to HTTP 400):
  - `create_po` — validates supplier is a PartnerType.SUPPLIER and all products exist;
    defaults line cost from product.
  - `mark_ordered` — only from draft.
  - `cancel_po` — blocked once anything was received or status is received/cancelled.
  - `receive_po` — validates PO is ordered, destination location is INTERNAL, no duplicate line ids,
    no over-receipt (qty ≤ remaining); writes SUPPLIER→INTERNAL stock moves per line through the M1
    ledger (`inventory_service.create_move`) with cost snapshot and `PO-{id}/{reference}` reference;
    flips status to received when every line is fully received.

### API
- `api/routers/purchasing.py`: `/api/purchase-orders` GET (?status= filter) / POST;
  `/{id}` GET; `/{id}/order`, `/{id}/receive`, `/{id}/cancel` POST. Responses converted to `POOut`.
- `main.py`: registered purchasing router under `/api`.

### Fixes during build
- Missing `utcnow` import in purchasing_service (NameError on order).
- Joined collection eager load requires `.unique()` on Result before `.all()` in list endpoint.
- Ruff auto-fixes: import sorting, unused imports (Location, utcnow).

### Verification
- New `smoke_test_m2.py` — **17/17 PASS**: draft creation w/ cost defaulting and total math
  (200×0.30+300×0.08=84), receive-before-order rejected, partial receipt updates ledger on-hand,
  over-receipt rejected (51>50), cancel blocked after partial receipt, full receipt → received status,
  move references/cost snapshots correct, ?status= filter, clean cancel flow.
- M1 `smoke_test.py` still passes unchanged (no regression).
- `ruff check app` clean. Test expectation bug fixed: total is 84 not 90 (test error, not API).

---

## [M1] Core inventory — 2026-08-24

### Backend foundation
- Initialized git repo, `.gitignore` (Python/Node/env/db artifacts), `PLAN.md`, `README.md`.
- Created `backend/pyproject.toml`: fastapi, uvicorn[standard], sqlalchemy>=2, pydantic v2,
  pydantic-settings; dev extras (pytest, httpx, ruff); ruff config (line-length 100, ignore B008/FURB157).
- `app/core/config.py`: pydantic-settings `Settings` — `database_url` (default SQLite `./erp.db`),
  `cors_origins` (localhost:3000), `.env` support, cached via `lru_cache`.
- `app/core/db.py`: engine + `SessionLocal` + `get_db()` FastAPI dependency (`check_same_thread=False`
  for SQLite only).

### Domain models (Odoo-mapped, see DECISIONS D-004/D-005)
- `models/base.py`: `Base(DeclarativeBase)`, `utcnow()`, `TimestampMixin`.
- `models/category.py`: `categories` (unique name, self-referencing parent).
- `models/product.py`: `products` (unique SKU/barcode, cost/sale_price Numeric, reorder_enabled,
  lead_time_days, safety_stock, is_active soft-delete flag).
- `models/partner.py`: `partners` with `PartnerType` enum (supplier/customer).
- `models/location.py`: `locations` with typed enum INTERNAL/SUPPLIER/CUSTOMER/LOSS, unique code.
- `models/stock_move.py`: `stock_moves` ledger — product, from/to locations, quantity > 0 check,
  unit_cost, reference, moved_at.

### Services
- `services/inventory_service.py`:
  - `on_hand_for_product()` — computed stock: sum into INTERNAL minus out of INTERNAL (joins Location).
  - `validate_move_locations()` — resolves codes, applies shorthand defaults (omit side → SUPPLIER/
    CUSTOMER), enforces transition allowlist.
  - `create_move()` — single commit path for the ledger.

### API (mounted under `/api`)
- `api/routers/inventory.py`:
  - `/api/products` GET (search q, category filter, include_inactive; response embeds live on_hand),
    POST; `/api/products/{id}` GET/PATCH/DELETE (soft).
  - `/api/catalog/categories` GET/POST (409 on duplicate name);
    `/api/catalog/partners` GET (?partner_type=)/POST.
- `api/routers/stock_moves.py`: `/api/stock-moves` GET (product filter, limit ≤500) / POST
  (validates direction; requires unit_cost when receiving from supplier).
- `main.py`: app factory, CORS, lifespan = `create_all` + seed default locations
  (SUPPLIER, SHOP, STORAGE, CUSTOMER, LOSS), `/api/health`.

### Fixes during build
- Fixed missing import of `Base` in `main.py` (lives in `app.models.base`, not `core.db`).
- Fixed invalid `Location.code.select()` → `select(Location.code)` in location seeding.
- Routers were mounted without prefix → added `prefix="/api"` so paths match PLAN.md API surface.
- Added `TYPE_CHECKING` imports to resolve relationship forward refs flagged by ruff (F821).
- Added `IntegrityError` handling → duplicate SKU/barcode/category return 409 instead of 500.

### Verification
- `smoke_test.py`: category → product → receive 100 → sell 35 → write off 2 → on-hand reports
  exactly **63.00** ✓; implicit-supplier receipt requires unit_cost ✓ (400 without, 201 with);
  invalid direction rejected ✓; no-direction move rejected ✓.
- `.venv\Scripts\ruff check app` → all checks passed.

### Tooling / environment notes
- Python 3.12.1, Node 22.11.0, npm 11.19.0, git 2.45.1 confirmed available.
- UIZZE skills (`ui-design`, `anti-ui-slop`) installed project-level at `.agents/skills/`
  for use from milestone M3 (dashboard UI design).
