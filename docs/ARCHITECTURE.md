# Architecture

## Runtime boundaries

The pnpm frontend is Next.js App Router, React, TypeScript and Tailwind 4. The independent uv/Python 3.13 API is FastAPI, Pydantic, SQLAlchemy 2, psycopg and Alembic. PostgreSQL belongs exclusively to Ficka. No shared package is needed.

Browser → typed frontend client → same-origin Next.js route handler → FastAPI → PostgreSQL. Runtime `API_INTERNAL_URL` stays on the web server. The financial adapter restricts resources and rejects cross-site JSON writes. API/database host ports remain unpublished in deployment. A future Sentinel integration must authenticate and authorize this boundary; origin checks are not authentication.

Frontend routes compose shared financial table, form and category components. Income and Expenses use type-specific labels with common implementation. Radix Dialog/AlertDialog handle centered modal focus, Escape and confirmations. Native input/select controls keep forms lightweight. Theme variables define the light appearance; financial data areas are fluid while forms and prose retain readable widths.

## API and persistence

Versioned API routes delegate to services; schemas validate requests and serialize decimal strings. SQLAlchemy models define `financial_entries` and `categories`. Request-scoped sessions close reliably; writes commit explicitly, database constraints guard invariants, and row locks protect update/category assignment operations. Soft deletion retains latest entry data, and category archival preserves references. See [FINANCIAL_ENTRIES.md](FINANCIAL_ENTRIES.md) for model fields, VAT assumptions, date semantics, endpoints and limitations.

Income/expense type is fixed by its route; detail/update/delete queries always include that type. Monetary calculations use Decimal and NUMERIC; frontend previews use decimal.js. VAT does not imply deductibility. Financial status and future recurring approval are separate concepts.

Alembic keeps baseline 0001 and adds revision 0002 without recreating the database. Model metadata is imported for consistency checking. Session advisory locking serializes online migration processes, including version-table initialization. API container startup runs migrations before starting its HTTP process, so failed migrations block new readiness. Future deployments with replicas may move this into a dedicated release step while retaining the lock.

Liveness is process-only. Readiness checks database connectivity. Central errors include a request ID and optional field messages without raw database errors. JSON application logs include request timing and IDs. CORS has only explicitly configured origins; normal web access uses the same origin.

## Hosting and checks

`compose.yaml` builds locally with loopback web publication; `compose.dev.yaml` adds a loopback DB port for native development. `docker-compose.yml` pulls prebuilt images, accepts LAN web access and keeps API/database internal. No new mandatory services or environment variables were added. See [DEVELOPMENT.md](DEVELOPMENT.md) and [DEPLOYMENT.md](DEPLOYMENT.md).

Main publishing is gated by frontend checks, backend tests, PostgreSQL migrations and Compose startup. The image-only Compose check also runs real browser financial flows. Native API integration tests use transaction/savepoint isolation; default unit tests need no database. Browser form tests cover errors/date behavior and requested screen widths; separate live tests exercise persisted records through web and API.

## Financial reporting

The read-only reporting service in `app/services/reporting.py` performs SQL aggregates and Decimal arithmetic independently of presentation. Versioned endpoints use explicit reporting schemas with decimal-string serialization. Actual cash uses paid/received payment dates; pending projections are separate; recorded VAT groups non-draft records by entry date. All queries exclude soft-deleted rows and restrict monetary aggregates to EUR, returning non-EUR exclusion counts. Cash buckets are zero-filled on calendar month/Monday-week boundaries.

Dashboard and Reports use typed same-origin requests through the existing adapter, allowlisting the six GET report endpoints. Recharts uses numeric coordinates only for display; exact amounts, shares and tooltips come from backend values. Request cancellation and keyed loading states prevent old period totals being displayed under new dates. Entry deep links reuse the existing financial detail modal without redesigning Income or Expenses.

No migration or deployment architecture change was required. Full rules, API contracts and limitations are in [REPORTING.md](REPORTING.md).

## Future modules

- **Advanced reporting:** exports, FX, account balances, live refresh and immutable historical snapshots. Current dashboard/cash-flow/category reports are implemented; recorded VAT remains separate and illustrative.
- **Recurring:** monthly generation on the 1st by default, idempotent proposals and separate approval state. Nothing is scheduled today.
- **VAT policy:** country-specific treatment, Belgium first, plus explicit deductibility. Existing rates/amounts remain snapshots on entries.
- **Recognition:** optional temporary document processing that proposes entries for confirmation, no permanent archive. OCR learning/Ollama remain optional and absent today.
- **Authentication:** Sentinel OIDC discovery/JWKS, issuer/audience/signature/expiry validation, secure sessions and CSRF handling. No direct access to Sentinel's database, no organization/RBAC framework and no authentication implemented yet.
