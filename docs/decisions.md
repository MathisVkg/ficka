# Ficka — Decisions

The decisions settled during planning (November 2026). Change one only on purpose, and note it here when you do.

## Product scope

- Ficka is a self-hosted tool for **visualizing and estimating** a small company's finances. It is not accounting software, not official tax accounting, and not document storage.
- Every total, VAT figure and forecast is an **estimation**. Ficka doesn't aim for 100% accounting precision.
- Principles: financial first, manual entry by default, intelligent assistance that is never mandatory.
- **v1:** one user and one company. Every business table already carries `company_id` (the foundation only). No roles, invitations or company switcher.

## Shared concepts

- **One proposal concept.** Anything Ficka suggests (from recurring, a document, or later a bank statement) is an entry with status `proposed`. The user confirms it, or rejects it, which deletes it.
- **Entry status** says whether it counts (`proposed`, `confirmed`). **Source** says where it came from (`manual`, `recurring`, `document`, `bank`). **Payment status** is derived from payments and never stored. Details: [database.md](database.md#status-reference).
- **No dedicated validation page.** Proposals appear through badges, a dashboard card and popups.
- **i18n from day one** (interface), and NL/FR/DE/EN keyword dictionaries for recognition.

## Ledger

- An entry is income or expense. **No credit notes. No investment flag.**
- The amounts live on **lines**. Entry totals are always computed from them.
- **Payments** are a separate table, so partial payments work. Payment sources: `manual`, `assumed`, `bank` (later).
- **Categories:** a default set at install. All are editable in Settings, and the user can create custom ones. Deleting a category that is still in use requires reassigning its entries first.
- All entries can be edited or deleted.
- **Currency:** EUR only in v1. The field exists.

## VAT

- VAT is **optional**. A line has a rate (21 / 12 / 6 / 0 %) or no VAT, for income and expenses alike.
- **Automatic calculation.** The VAT is computed from the net, or from the gross when "amounts include VAT" is on. A VAT amount stated on the document, or typed by the user, overrides the calculation (`vat_manual`). A "recalculate" action resets it.
- Rates are **configuration data with validity dates**, per country. Belgium is the default.
- Quarterly summary: collected VAT, VAT on expenses, estimated balance, breakdown by rate, and warnings for proposals that aren't confirmed yet.
- **Out of scope:** deductibility percentages, reverse charge, the declaration-box view, the small-business exemption.

## Recurring

- **Settings:**
  - Generation timing: "all on the 1st of the month" (default) or "on each due date".
  - Validation: manual review (default) or automatic.
- **Variable-amount templates are always reviewed**, whatever the setting.
- **Automatic mode** creates the confirmed entry **and** its payment (source `assumed`, on the due date), and sends a summary notification.
- Generation is **idempotent**: one occurrence per (template, period). It catches up on startup if the server was off.
- Templates are **versioned**: a price change applies from a date onwards, and past entries keep their amounts.
- Deleting a generated entry marks its occurrence as skipped, so it isn't regenerated.
- **Not in v1:** a per-template override of the global settings.

## Recognition

- **The original file is never stored**, neither in the database nor permanently on disk.
  - It sits in a temporary folder (tmpfs in Docker if possible) only while it's processed and reviewed.
  - It is deleted on confirm or reject, and abandoned files are deleted after a configurable delay (default 24 hours).
  - Ficka keeps only the financial data, the file hash (duplicate detection), an optional link to where the user stores the original, and the supplier memory (label patterns and positions, not content).
- **Pipeline, cheapest and most reliable first:** Peppol UBL XML → Factur-X → PDF text layer → OpenCV + OCR (Tesseract, then PaddleOCR) → deterministic validators → supplier memory → optional LLM.
- **The companion**: background processing, a status chip, then the **normal entry form** pre-filled.
  - **Every field shows its confidence score**: a dot always, plus the percentage next to the field or on hover, depending on space.
  - Every field shows its source.
  - Totals are always checked arithmetically.
- **Learning** comes from validated mappings and user corrections. No model training is needed.
- **LLM:** optional, local only (Ollama), behind the same extractor interface. Its role (second opinion, fallback when extraction fails, or both) will be decided from benchmark results. The application must work fully without it.
- **Lab tooling:** `ficka eval` runs the extractors over an anonymized test set and reports per-field accuracy and calibration.

## Dashboard

- Four figures: result (month and year to date), receivables, payables, VAT estimate for the quarter.
- Charts: income vs expenses over 12 months, a 3-month cash forecast (unpaid entries + recurring templates), expenses by category.
- An attention card: proposals waiting, overdue invoices, documents ready.
- The **starting balance** is configured in Settings, which gives the forecast a real level.

## Later versions (not v1)

- Bank statement import (CODA, CAMT.053, CSV with remembered column mapping), with proposal-based matching on structured reference, IBAN and amount. No bank API connection.
- Multiple companies and users on top of the existing foundation.

## Stack

| Layer | Choice |
|---|---|
| Backend | Python, FastAPI, SQLModel/SQLAlchemy, Alembic |
| Database | SQLite |
| Background jobs | Job table + in-process worker (no Celery or Redis) |
| Documents | lxml, factur-x, pdfplumber, OpenCV, Tesseract, PaddleOCR; Ollama optional |
| Frontend | SvelteKit (TypeScript), Tailwind CSS v4, bits-ui, Apache ECharts |
| Motion | Svelte transitions + Anime.js v4, respecting `prefers-reduced-motion` |
| Deployment | Docker Compose services `api` + `web` + optional `ollama`; images built by GitHub Actions and published to GHCR; Portainer deploys `deploy/portainer-compose.yml` with the Repository method; no build on the server |

## Deployment

- The server is managed through Portainer, reached through the Portainer agent, which can't run image builds (BuildKit fails with `http2: frame too large`). So **nothing is built on the server**.
- GitHub Actions (`.github/workflows/images.yml`) builds `ficka-api` and `ficka-web` on every push to `main` and publishes them to GHCR, tagged `latest` and `sha-<short sha>`.
- Portainer deploys `deploy/portainer-compose.yml` (Stacks → Repository), which only pulls the images. `docker-compose.yml` stays for local builds; the two files are kept aligned.
- GHCR is used at deploy time only; the running app has no external dependency.

## Design

- Professional and calm: a warm off-white background (`#F7F6F2`), white surfaces with thin borders (no heavy shadows), lots of space.
- **Accent:** petrol green `#1F5C5A`, used sparingly (active navigation, primary actions, chart highlight).
- Muted green for income and muted rose for expenses, never saturated.
- **Font: Geist** for everything, with tabular figures for amounts.
- A slim, collapsible left navigation.
- Calm motion (150–300 ms, ease-out).
- Mockup reference: the "Ficka — Design mockup" canvas. It's a direction, not a final design; it still has the earlier fonts.
