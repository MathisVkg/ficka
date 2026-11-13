# Income, expenses and categories

## Model and status semantics

Income and Expenses have separate pages and API routes backed by `financial_entries`. UUID identifiers, type, title, positive total including VAT, ISO currency/country codes, optional category/counterparty, entry date, payment date, status, VAT rate/amount, manual VAT flag, notes, timezone-aware creation/update timestamps and a soft-deletion timestamp are persisted.

Amounts use PostgreSQL `NUMERIC(14,2)` and Python Decimal. VAT rates use `NUMERIC(7,4)`, from 0 to 100. Financial API decimal values are strings; amounts always serialize with two places and rates with four. JSON floating-point money/rates are rejected. Send `"121.00"`, not `121.0`. The UI uses decimal.js for its preview; JavaScript Number is used only for locale formatting, not financial arithmetic.

| Internal status | Income label | Expense label | Future calculation rule                              |
| --------------- | ------------ | ------------- | ---------------------------------------------------- |
| `draft`         | Draft        | Draft         | Excluded from actual and projected totals            |
| `pending`       | Pending      | Pending       | Projected movement only, using expected payment date |
| `paid`          | Received     | Paid          | Actual movement, using actual payment date           |

Core fields remain required even for a draft. Status changes are allowed in either direction to support correction. There is no approval state or recurring processing in this implementation. Overdue is derived in the UI when a pending entry's payment date precedes the browser's current date; it is not a database status.

No dashboard aggregation engine is implemented. Dashboard positions remain neutral and explicitly say summaries are not calculated. Entries must never be summed across currencies without a future conversion policy. Future actual cash flow must select only paid, non-deleted entries; VAT reporting is a separate calculation boundary.

## Date behavior

The creation form defaults both dates to the browser's current calendar date. Changing entry date updates payment date until the user manually edits payment date. **Match entry date** resets it and explicitly relinks the fields. Editing an existing entry starts unlinked and preserves both saved dates, even if they happen to be equal.

The API defaults entry date to its current date when omitted and payment date to entry date on creation. PATCH never silently synchronizes saved dates. Dates must be valid YYYY-MM-DD calendar dates, not timestamps. Date-range filters refer to entry/invoice date and include both endpoints; reversed ranges are rejected.

For pending entries, payment date is expected. Paid/Received uses the same field as the actual date. The quick action opens the edit modal with today's actual payment date for confirmation; changing status in the full form also makes the actual date explicit. Future actual payment dates are rejected. Browser and API calendar clocks should agree; business timezone configuration is not implemented yet.

A payment may precede the entry date, for example for an advance payment. Partial payments, separate expected-versus-actual history and payment allocations are not represented. Moving to paid replaces the expected date with the confirmed actual date; earlier payment-date values are not retained as a payment history.

## VAT assumptions

Belgium (BE) and EUR are per-entry defaults. The UI offers 0%, 6%, 12% and 21% suggestions plus a custom rate. It does not decide which rate legally applies.

Given a VAT-inclusive total T and percentage R:

```text
VAT = round_half_up(T × R / (100 + R), 2)
Net excluding VAT = T − rounded VAT
121.00 at 21% → VAT 21.00, net 100.00
```

A manual VAT amount must be between zero and the total, with at most two decimal places. The explicit `vat_overridden` flag preserves manual values when other fields change. For automatic entries, changing amount or rate recalculates VAT. PATCH `vat_amount: null` clears an override and returns to automatic calculation. Clearing the form's override field does the same. A zero rate and zero VAT represents an entry without VAT.

This is recorded VAT, not a tax return or a definitive estimate. Deductibility is not assumed. Exemptions, reverse charge, mixed/private use, country tax rules, VAT treatment and partial deductibility are future work. All supported currency codes currently use the requested two-decimal entry precision; currency-specific minor-unit rules and FX are not implemented.

## Categories and deletion

Categories have UUID, name, income/expense type, optional hex color and active flag. Revision 0002 inserts eight initial suggestions: Services, Product sales, Other income, Office & supplies, Software, Travel, Professional services and Other expenses. It inserts **no financial entries**.

Names are unique per type after trimming, collapsing whitespace and Unicode case folding. Income and expenses can use the same category name. A category's type cannot be changed. Renaming changes the display name on historical entries while preserving their references. Archived names remain reserved within their type; restore or rename an existing category rather than creating an ambiguous duplicate.

Settings supports create, rename, archive and restore. Archiving stops new assignments but preserves existing links; an edit may retain an already assigned archived category. Filters include archived categories so historical entries remain discoverable. Foreign keys use RESTRICT; there is no category delete endpoint.

Entry DELETE requires confirmation in the UI and sets `deleted_at`. The row and its latest stored financial values remain in PostgreSQL. It disappears from normal list/detail/update endpoints and future calculations. There is no restore UI/API or permanent deletion endpoint yet. Timestamps and tombstones preserve the latest record, not an immutable audit log of every edit.

## API

All routes are under `/api/v1`. Income routes cannot read, update or delete expenses and vice versa. Request-scoped SQLAlchemy sessions and explicit commits handle writes; failures roll back. Errors follow `{error: {code, message, request_id, fields?}}` without database details.

| Method               | Path               | Behavior                                     |
| -------------------- | ------------------ | -------------------------------------------- |
| GET / POST           | `/income`          | List / create income                         |
| GET / PATCH / DELETE | `/income/{id}`     | Read / partial update / soft-delete income   |
| GET / POST           | `/expenses`        | List / create expenses                       |
| GET / PATCH / DELETE | `/expenses/{id}`   | Read / partial update / soft-delete expenses |
| GET / POST           | `/categories`      | List / create categories                     |
| PATCH                | `/categories/{id}` | Rename, recolor, archive or restore          |

Entry lists accept `page` (default 1), `page_size` (default 20, max 100), `date_from`, `date_to`, `status`, `category_id`, `search`, `sort=date|amount|created_at` and `direction=asc|desc`. Text search covers title, counterparty and notes; wildcard characters are treated literally. Responses contain `items`, `total`, `page` and `page_size`. Stable ID tie-breaking is applied to sorting. Category lists are flat and accept optional `type=income|expense` and `active=true|false`.

Create returns 201, reads/updates 200 and deletion 204. Missing/deleted/wrong-type IDs return 404; invalid fields return 422; category-name conflicts return 409. Extra body properties are rejected. OpenAPI request/response schemas are available at API `/docs` when accessed privately.

Example create body:

```json
{
  "title": "Website design",
  "amount": "121.00",
  "currency": "EUR",
  "country": "BE",
  "entry_date": "2026-01-05",
  "payment_date": "2026-01-20",
  "status": "pending",
  "vat_rate": "21"
}
```

## Web integration and deployment

The browser calls a typed same-origin client. Next.js forwards only income, expenses and categories resources through the existing server-only `API_INTERNAL_URL`. JSON writes reject cross-site browser origins. No internal Docker hostname is sent to the browser and no SQL runs in frontend code. This boundary is ready for future Sentinel session integration, but there is still no authentication or authorization in this release; keep deployment private.

Revision `0002` follows the preserved `0001` baseline and adds the two tables, constraints, indexes and category suggestions. Online Alembic commands take a PostgreSQL session advisory lock, waiting up to 60 seconds for another migration. The existing API image startup still runs `alembic upgrade head && uvicorn …`; a failed migration prevents the new process from serving readiness. A PostgreSQL role must be allowed to create the schema objects.

Back up the deployed database and record image digests before upgrading. Deploy matching API/web images after CI publishing succeeds. Do not reset volumes. Downgrading to 0001 drops the financial tables and their data; only test that downgrade against a disposable database. Automatic rollback of financial schema/data is not provided.

No new mandatory services or environment variables were added. The existing `main → GitHub Actions → GHCR → Portainer → orion-01` path and internal API/database networking remain in place.
