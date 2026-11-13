# Ficka

Self-hosted financial tracking for small businesses. This repository contains the **project foundation**, not a finished accounting product.

## Start with Docker

Install Docker Desktop with Linux containers (Windows) or Docker Engine with Compose v2 (Linux).

1. Copy `.env.example` to `.env` (PowerShell: `Copy-Item .env.example .env`).
2. Replace the PostgreSQL password with a long random URL-safe value. Keep the local `DATABASE_URL` consistent if you also use native development.
3. Run `docker compose up --build --wait`.
4. Open [Ficka](http://localhost:3000). The dashboard checks API/database readiness automatically.

Only the web port is published, bound to loopback by default. PostgreSQL data persists in a named volume. Migrations run before API startup.

| Action              | Command                                                                                                                                       |
| ------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| Start               | `docker compose up -d --wait`                                                                                                                 |
| Stop, preserve data | `docker compose down`                                                                                                                         |
| Rebuild             | `docker compose up -d --build --wait`                                                                                                         |
| Inspect             | `docker compose ps`                                                                                                                           |
| Logs                | `docker compose logs -f --tail=100`                                                                                                           |
| Migration status    | `docker compose exec api alembic current`                                                                                                     |
| Liveness            | `docker compose exec api python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/api/v1/health/live').read())"` |

## What works today

- Six responsive application routes, shared navigation, empty dashboard and period selector.
- Typed readiness boundary with connection failure and retry UI.
- Versioned FastAPI health endpoints, PostgreSQL sessions, Alembic baseline, consistent API errors and structured logs.
- Frozen frontend/backend dependencies, linting, type checks, browser smoke tests and CI with PostgreSQL and Compose checks.

Entry creation, scheduling, financial calculations, reports, OCR and sign-in are **not implemented**. Empty values mean no data; they are never demo company figures.

## Development and design

See [development](docs/DEVELOPMENT.md), [architecture](docs/ARCHITECTURE.md) and [product scope](docs/PRODUCT_SCOPE.md). The UI follows the supplied written light Version B direction; a reference image was not supplied.

Next.js 16.4.6 was resolved from the stable 16 release line. The [November security release](https://nextjs.org/blog/november-2026-security-release) establishes 16.4.5 as the patched floor.
