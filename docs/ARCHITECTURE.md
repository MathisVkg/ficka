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

## Future modules

- **Cash flow/reporting:** aggregate persisted, non-deleted entries with correct draft/pending/paid rules and explicit currency policy. Dashboard summaries are deliberately not calculated yet. VAT reporting stays separate from cash flow.
- **Recurring:** monthly generation on the 1st by default, idempotent proposals and separate approval state. Nothing is scheduled today.
- **VAT policy:** country-specific treatment, Belgium first, plus explicit deductibility. Existing rates/amounts remain snapshots on entries.
- **Recognition:** optional temporary document processing that proposes entries for confirmation, no permanent archive. OCR learning/Ollama remain optional and absent today.
- **Authentication:** Sentinel OIDC discovery/JWKS, issuer/audience/signature/expiry validation, secure sessions and CSRF handling. No direct access to Sentinel's database, no organization/RBAC framework and no authentication implemented yet.
