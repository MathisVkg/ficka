# Architecture

## Runtime boundaries

The pnpm workspace contains `apps/web` (Next.js App Router, React, TypeScript, Tailwind 4). `apps/api` is an independent Python 3.13/uv project (FastAPI, Pydantic, SQLAlchemy 2, psycopg, Alembic). No shared package is needed yet. PostgreSQL 17 belongs exclusively to Ficka.

Browser → Next.js route handler → FastAPI → PostgreSQL. The browser uses the typed `src/lib/api/client.ts` boundary and a same-origin readiness route. Runtime `API_INTERNAL_URL` stays on the web server. API and database ports need not be published. The adapter currently exposes only readiness, not an unrestricted proxy.

API routes delegate to services; Pydantic schemas describe HTTP payloads; SQLAlchemy models will live in `app/models`; sessions are request-scoped and always closed. Future write services must explicitly commit or roll back transactions. No financial models exist. The initial no-op migration establishes the Alembic version table; future model modules must be imported into migration metadata.

Liveness is process-only. Readiness executes `SELECT 1` with a bounded connection timeout and returns 503 on database failure. Errors use `{error: {code, message, request_id}}`, without database details. Request IDs correlate JSON application logs and response headers. CORS defaults to no cross-origin access and accepts only the explicit configured origin list; there is no wildcard.

## Future modules (not implemented)

- **Entries:** separate Income and Expenses UI, shared service rules where justified. Draft, Pending and Paid/Received are financial statuses.
- **Recurring:** a proposal approval state separate from financial status. Generate monthly proposals on the 1st by default; introduce explicit scheduling, idempotency and transaction rules with the feature.
- **Reports/VAT:** aggregate owned entries, country-specific policy boundary, Belgium first. Estimates must be clearly distinguished from filed tax returns.
- **Document recognition:** optional worker/adapter preparing suggested entries for user confirmation. Temporary processing, no permanent document archive. Optional learning and Ollama must not be runtime prerequisites.
- **Authentication:** Sentinel is an OIDC identity provider. Future integration uses discovery/JWKS and verifies issuer, audience, expiry and signatures; no direct Sentinel database access. Choose secure web session and CSRF handling as part of that implementation. No authentication, authorization, organization or RBAC framework exists today.

## UI and hosting

CSS variables own colors and radii. The small Button component follows shadcn/ui composition with Radix Slot; `components.json` supports future shadcn additions. Lucide supplies icons. Recharts is installed for future real charts; empty views draw no fictional time series. Dark theme tokens can be added later.

Compose runs one API process with migrations before startup, appropriate for this foundation. Multiple API replicas require a separate one-shot migration deployment step. Containers run as non-root users. `compose.yaml` builds locally and binds web to loopback; `compose.dev.yaml` adds a loopback database port for native development. The separate image-only `docker-compose.yml` publishes web on the host LAN and keeps API/database internal. Main CI publishes GHCR images only after the reusable checks pass. Deployment, registry access and backup instructions are in [DEPLOYMENT.md](DEPLOYMENT.md). The application has no authentication yet; keep it on a trusted LAN/private network.
