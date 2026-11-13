# Ficka

Self-hosted financial tracking for small businesses. Income and Expenses now support persistent entries, date/status management, precise VAT recording, filtering, pagination and safe deletion. Settings manages reusable categories. Dashboard and Reports aggregate real EUR financial data. Recurring processing, OCR, sign-in and advanced VAT accounting remain future modules.

## Choose how to run it

| Mode                | Configuration                                                   | Application runtime          | Access                         |
| ------------------- | --------------------------------------------------------------- | ---------------------------- | ------------------------------ |
| Windows development | Root `.env`, `compose.yaml` + `compose.dev.yaml` for PostgreSQL | Native pnpm web + uv API     | localhost:3000                 |
| Local Docker build  | `compose.yaml`                                                  | Builds web/API from source   | localhost:3000 only            |
| Portainer / homelab | `docker-compose.yml`                                            | Pulls GHCR images; no builds | Docker host's LAN address:3000 |

Always specify `-f` in Docker commands. The two root Compose files are alternatives; do not combine them. `compose.dev.yaml` is only the native-development database port overlay.

## Windows quick start

Install Node.js 24, pnpm 11.25.0, uv and Docker Desktop with Linux containers. Full installation and external-database instructions are in [DEVELOPMENT.md](docs/DEVELOPMENT.md).

```powershell
Set-Location C:\Users\zeyros\Documents\repository\ficka
Copy-Item .env.example .env
# Edit .env: replace POSTGRES_PASSWORD. Do not overwrite an existing .env.
pnpm install --frozen-lockfile
uv python install 3.13
uv sync --project apps/api --frozen
pnpm dev:db
Set-Location apps/api
uv run --env-file ../../.env alembic upgrade head
uv run --env-file ../../.env uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

In a second terminal at repository root run `pnpm dev`, then open [Ficka](http://localhost:3000). Set the PostgreSQL password once: both the database and API use it. Native configuration uses 127.0.0.1; Compose supplies internal `db` and `api` service names automatically.

## Local Docker build

After preparing `.env`, run `docker compose -f compose.yaml up --build --wait`. Stop with `docker compose -f compose.yaml down`; inspect with `docker compose -f compose.yaml logs -f --tail=100`. Named database volumes survive normal stops. Stop native API/web processes before switching modes.

## Portainer and publishing

[DEPLOYMENT.md](docs/DEPLOYMENT.md) covers the complete Git stack setup, environment values, GHCR permissions, LAN access, updates and troubleshooting. Choose repository branch `main` and Compose path **`docker-compose.yml`**. This avoids Portainer's source-build path.

Main pushes run all checks before publishing `ghcr.io/mathisvkg/ficka-web` and `ghcr.io/mathisvkg/ficka-api`, tagged `main` and `sha-<full-commit-sha>`. Wait for a successful **Publish images** workflow before deploying. Set each package public or give Portainer GHCR pull credentials.

## Financial entry management

After applying migrations, open Income or Expenses and use **New income** / **New expense**. Centered forms preserve edited payment dates and support VAT presets or manual amounts. Entries use Draft, Pending and Paid/Received states. Settings manages categories without deleting historical references. See [financial behavior and API](docs/FINANCIAL_ENTRIES.md). Dashboard and Reports show actual paid/received cash flow, separate pending projections, category breakdowns and illustrative recorded VAT. Non-EUR entries are excluded explicitly; no exchange rates or definitive tax liability are inferred. See [reporting rules and API](docs/REPORTING.md).

Revision 0002 adds the financial tables and suggested categories without resetting the database. API image startup applies it before serving. Back up the database before redeploying matched API/web images through the existing Portainer workflow. No new services or environment variables are required.

## Quality and scope

Run `pnpm lint`, `pnpm typecheck`, `pnpm format:check`, `pnpm test`; backend checks are in [DEVELOPMENT.md](docs/DEVELOPMENT.md). Both dependency lockfiles are committed. Browser tests cover financial forms, desktop/mobile routes, date synchronization, save errors, deletion and five viewport widths. CI also tests real PostgreSQL, both Compose modes and browser flows against persisted entries.

See [architecture](docs/ARCHITECTURE.md) and [product scope](docs/PRODUCT_SCOPE.md). No demo figures are displayed as company data. The application has no authentication yet; use a trusted LAN or private reverse proxy.

Task 03 requires no schema migration or new service/configuration. Period, monthly/weekly cash-flow and annual VAT controls are functional; pending links reuse the existing entry details. Existing CI also verifies persisted reporting totals before image publication.
