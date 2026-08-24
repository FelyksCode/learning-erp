# Deployment

## Local development (default)

Backend uses SQLite (`backend/erp.db`), tables auto-created on startup, admin **admin/admin** seeded.

```bash
# terminal 1
cd backend && .venv\Scripts\uvicorn app.main:app --reload

# terminal 2
cd frontend && npm run dev        # http://localhost:3000
```

## Docker Compose (PostgreSQL)

Requires Docker. Builds both images and starts Postgres 16:

```bash
docker compose up --build
```

- Frontend: http://localhost:3000 (API URL baked at build time via `NEXT_PUBLIC_API_URL`, default `http://localhost:8000/api`)
- Backend API + docs: http://localhost:8000/docs
- DB: postgres 16, user/pass/db `erp/erp/erp`, data in the `pgdata` volume
- Migrations run via Alembic — from inside the backend container:
  ```bash
  docker compose exec backend alembic upgrade head
  ```
- `AUTO_CREATE_TABLES=false` in compose; for a fresh Postgres DB run the command above once.
  (Dev SQLite keeps auto-create unless `AUTO_CREATE_TABLES=false`.)

### Environment variables

| Variable | Where | Default | Notes |
|----------|-------|---------|-------|
| `DATABASE_URL` | backend | `sqlite:///./erp.db` | `postgresql+psycopg://user:pass@host:5432/db` for Postgres |
| `AUTO_CREATE_TABLES` | backend | `true` | Set false when using Alembic |
| `JWT_SECRET` | backend | dev default | **Set 32+ random bytes in production** |
| `JWT_EXPIRE_MINUTES` | backend | `720` | Token lifetime (12h) |
| `AI_ENABLED` / `AI_API_KEY` / `AI_BASE_URL` / `AI_MODEL` | backend | false / — / openai / gpt-4o-mini | Optional LLM insights |
| `CORS_ORIGINS` | backend | `["http://localhost:3000"]` | JSON list of allowed frontend origins |
| `NEXT_PUBLIC_API_URL` | frontend build arg | `http://localhost:8000/api` | Baked into the bundle at build time |

## First login & security notes

1. Log in at the frontend with **admin / admin**.
2. Immediately change it (admin UI/users endpoint or `PATCH /api/auth/users/{id}` with a new password).
   The seeded password is documented here, so treat any deployment using it as compromised until changed.
3. Generate a strong secret: `python -c "import secrets; print(secrets.token_hex(32))"`.

## Building images individually

```bash
docker build -t erp-backend ./backend
docker build -t erp-frontend --build-arg NEXT_PUBLIC_API_URL=https://api.example.com/api ./frontend
```
