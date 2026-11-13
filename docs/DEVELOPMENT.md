# Development

## Prerequisites

Node.js 24, pnpm 11.25.0, uv 0.13.8, Python 3.13 (uv can install it), Docker with Compose v2. Run commands from the repository root unless stated otherwise. Never commit `.env`.

## Native web/API with containerized PostgreSQL

Copy `.env.example` to `.env` and change the password. Compose intentionally publishes no database/API port. For native development create an **untracked** override, for example `compose.local.yaml`, with:

```yaml
services:
  db:
    ports:
      - "127.0.0.1:5432:5432"
```

Run `docker compose -f compose.yaml -f compose.local.yaml up -d db --wait`. Then:

```powershell
pnpm install --frozen-lockfile
uv python install 3.13
Set-Location apps/api
uv sync --frozen
uv run --env-file ../../.env alembic upgrade head
uv run --env-file ../../.env uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

In a second terminal at root run `pnpm dev`. Web defaults to the API at 127.0.0.1:8000. Override `API_INTERNAL_URL` in the web process environment if needed. FastAPI docs: [OpenAPI UI](http://127.0.0.1:8000/docs).

## Checks

```powershell
pnpm lint
pnpm typecheck
pnpm format:check
pnpm build
pnpm --filter @ficka/web exec playwright install chromium
pnpm test
Set-Location apps/api
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

Browser tests run a production build and exercise all routes on desktop/mobile, empty values, overflow and the connection failure/retry path. Unit API tests override the session and need no database. For a real database readiness test after migrating: set `RUN_DB_TESTS=1` in the environment and run `uv run --env-file ../../.env pytest tests/integration`. CI runs real PostgreSQL migrations up/down, metadata consistency and readiness, plus a full Compose boot.

Format frontend/config/docs with `pnpm format` and Python with `uv run ruff format .`. Update dependencies deliberately and commit `pnpm-lock.yaml` and `apps/api/uv.lock`. Installs in CI/Docker are frozen.

## Database changes

From `apps/api`, use `uv run --env-file ../../.env alembic revision --autogenerate -m description`, review the migration, then `uv run --env-file ../../.env alembic upgrade head`. Test upgrade/downgrade on a disposable database. Do not use `metadata.create_all` in application startup.

## Troubleshooting and deployment

Use `docker compose ps` and `docker compose logs --tail=100 api db web`. Readiness failures usually mean a wrong database URL/password or an unhealthy database. Changing POSTGRES_PASSWORD after volume initialization does not change the existing database password; rotate it explicitly. Use URL-safe credentials (or percent-encode username/password in DATABASE_URL).

The volume survives `docker compose down`. `docker compose down -v` destroys its data and is for disposable environments only. Back up PostgreSQL before deployments. Portainer build and registry guidance is in ARCHITECTURE.md; Dockerfiles use Linux images and work with Windows Docker Desktop Linux containers. This foundation has no sign-in yet; keep it private.
