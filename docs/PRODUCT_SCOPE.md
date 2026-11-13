# Product scope

Ficka is self-hosted small-business financial tracking software.

## Available now

- Responsive application shell and six navigation routes with a fluid desktop main area.
- Separate persistent Income and Expenses workflows: create, details, edit, status confirmation and soft deletion.
- Server-backed entry-date ranges, status/category filters, text search, sorting and pagination.
- Centered, scrolling create/edit dialogs with linked creation dates, independent edit dates, precise VAT preview, inline errors and unsaved-change confirmation.
- Reusable income/expense categories in Settings, including custom names, colors, archiving and restoration.
- PostgreSQL NUMERIC/Decimal amounts, UUID records, timezone-aware metadata and Alembic migrations.
- Versioned API, typed same-origin integration, health checks, tests and image-based deployment.

Dashboard and Reports now show real EUR financial aggregates, actual/expected cash-flow views, category breakdowns, recorded VAT quarters and pending movements. Filters, zero-filled timelines, currency exclusions and appropriate empty/error states are implemented. VAT remains illustrative. Recurring remains an explanatory future page; company configuration and authentication are not implemented.

## Financial semantics

Draft entries are excluded from calculations. Pending entries represent expected movement; paid entries represent actual movement, labeled Received for income. Approval state remains a separate future concept. Both entry and payment dates are stored; expected/actual payment date currently shares one field. Details and limits are in [FINANCIAL_ENTRIES.md](FINANCIAL_ENTRIES.md).

Belgium and EUR are defaults, with suggested VAT rates and manual overrides. This is basic VAT recording, not a tax engine or deductibility determination.

## Planned, not implemented

Recurring proposal generation (monthly on the 1st by default) with separate human approval; report exports, FX/account balances and advanced country-aware VAT policy; Sentinel OIDC; temporary OCR-assisted preparation requiring user confirmation. Optional OCR learning and Ollama must never be main-application prerequisites.

Partial payments, immutable edit history, soft-delete restoration, FX and currency-specific minor units, business timezone settings and advanced VAT treatments are not available. No generic organization/RBAC or multi-tenant framework is introduced. Redis, Celery, permanent document archives and heavy recognition services remain outside scope.

Reporting rules, API endpoints and limitations are documented in [REPORTING.md](REPORTING.md).
