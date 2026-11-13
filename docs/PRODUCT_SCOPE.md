# Product scope

Ficka is financial-first, self-hosted small-business software. Today it supplies infrastructure and a usable empty shell only.

## Included in Task 01

Dashboard, Income, Expenses, Recurring, Reports and Settings routes; navigation; responsive light theme; neutral empty KPI/chart/category/payment areas; a compact recurring approval explanation; backend readiness integration; API/database/migration infrastructure; development checks and documentation.

The period selector changes the empty dashboard's selected scope. No entries exist, no amount is calculated, and no financial operations are implied by navigation links. Secondary pages explicitly explain future availability.

## Planned

Income/expense management with Draft, Pending and Paid/Received statuses; recurring proposal generation (monthly on the 1st by default) and separate human approval; cash-flow visualization; reporting and country-configurable VAT, initially Belgium; Sentinel OIDC sign-in; optional OCR-assisted preparation requiring confirmation.

Document processing is temporary, without permanent storage. Optional OCR learning and Ollama integrations must leave the main application functional when disabled.

## Excluded

Full accounting, financial tables, authentication, generic tenancy, organization/RBAC, Redis, Celery, Ollama, PaddleOCR and permanent document archives are outside this foundation. No scheduled financial action happens today.
