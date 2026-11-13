# Financial dashboard and reports

## Calculation contract

Authoritative totals are read-only PostgreSQL aggregates over persisted entries. Python Decimal handles differences, sums of already-aggregated category groups and percentage allocation. Responses serialize money/percentages as two-decimal strings. No reporting totals are computed by downloading and summing entries in the browser.

Every report excludes soft-deleted entries and Drafts. The reporting currency is fixed to **EUR**: other currencies are never added or converted. Each endpoint reports how many otherwise-relevant non-EUR entries were excluded. There are no exchange rates. Counts are specific to each report's dates/status basis; cash and VAT exclusion counts may refer to the same entry and should not be added as a unique transaction count.

| Report                                            | Included statuses | Date basis              | Amount                                        |
| ------------------------------------------------- | ----------------- | ----------------------- | --------------------------------------------- |
| Actual cash flow, summary and category breakdowns | `paid`            | Actual `payment_date`   | Stored total including VAT                    |
| Expected cash flow and pending movements          | `pending`         | Expected `payment_date` | Stored total including VAT                    |
| Recorded VAT overview                             | `pending`, `paid` | `entry_date`            | Stored VAT amount, including manual overrides |

Income uses Received terminology in the UI; its internal paid status remains unchanged. Net cash flow is actual received income minus paid expenses, not a bank balance. Expected net is a movement difference, not a forecast starting balance. VAT is independent of cash-flow calculation.

### Date boundaries

Date filters include both endpoints and operate on stored calendar DATE values. There is no timestamp/UTC conversion of financial dates. Monthly grouping uses calendar months. Weekly grouping uses Monday-start weeks; the first/last bucket is clipped to the requested range. Every bucket in the requested timeline is returned, including genuine zero-activity months/weeks.

Both `date_from` and `date_to` must be supplied together or both omitted. Defaults are the API server's current calendar month. Allowed dates are 1900–2100, and a range is limited to 1,831 inclusive days to bound chart payloads. Reversed, invalid or excessive ranges return 422. The web UI supplies explicit dates based on the browser calendar, so it does not depend on the server timezone for period selection.

The UI also sends an explicit browser-calendar `as_of` date for overdue comparison. Pending entries are overdue only when expected payment date is strictly earlier than that date; a payment expected today is not overdue. Direct API callers may supply `as_of`; its default is the server calendar date. This parameter changes overdue labeling, not historical entry statuses. Reports reflect the currently saved records/statuses, not an immutable historical snapshot.

### Category proportions

Categories include archived historical references and Uncategorized entries. Grouping uses category ID, current name and color. Percentages are allocated to hundredths of a percent using largest remainders so displayed shares sum to exactly 100.00% when spending/income exists. Empty results have no category rows and no division by zero.

The dashboard donut contains all categories and uses their recorded colors where available. Its compact legend shows the six largest categories; the full ranked Reports breakdown includes every category. Renaming a category updates its display name in historical reports, consistent with the existing entry model.

### Recorded VAT, not a tax calculation

Output VAT is recorded VAT on income; input VAT is recorded VAT on expenses. The illustrative difference is output minus input. Stored manual VAT overrides are used without recalculation.

Expense VAT is **not assumed deductible**. Belgian tax-point rules, exemptions, reverse charge, mixed/private use and country-specific VAT treatment remain unimplemented. Calendar-quarter grouping by entry date is an illustration, not a determination of legal VAT periods. The difference must not be interpreted as tax payable, a refund or a filed return.

The selected-period dashboard VAT metric uses entry dates, including Pending and Paid/Received. The Reports VAT section has a separately labeled reporting-year selector and always shows all four calendar quarters. Changing the main period initially aligns that year with the selected range end; users can then inspect another VAT year independently.

## Reporting API

All endpoints are GET-only under `/api/v1/reports`:

| Endpoint              | Parameters                                                               | Response                                                                                                                          |
| --------------------- | ------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------- |
| `/summary`            | Shared date range                                                        | Actual and expected income/expenses/net/counts; recorded VAT output/input/difference; separate cash/VAT currency exclusion counts |
| `/cash-flow`          | Shared dates, `grouping=month                                            | week`, `basis=actual                                                                                                              | expected`                                                                                                      | Continuous bucket list with dates, income, expenses, net and counts |
| `/expense-categories` | Shared dates                                                             | Paid EUR expense total and ranked category amounts/shares                                                                         |
| `/income-categories`  | Shared dates                                                             | Received EUR income total and ranked category amounts/shares                                                                      |
| `/pending`            | Dates for `scope=period`; or `scope=all`; optional `as_of`, `type=income | expense`, `page`, `page_size`                                                                                                     | Expected totals, overdue count, currency exclusions and a bounded list ordered by expected payment date and ID |
| `/vat`                | `year` (1900–2100; default current server year)                          | Four recorded-VAT quarter rows and annual totals                                                                                  |

Pending defaults to selected-period scope, page 1 and page size 20 (max 100). All-outstanding scope rejects date-range arguments rather than silently ignoring them. Pending rows contain entry IDs/types for navigation. Summary, category, cash-flow and VAT endpoints use one aggregate query each; pending uses one aggregate plus one bounded page query, without N+1 relationship loading.

Example:

```text
GET /api/v1/reports/summary?date_from=2026-01-01&date_to=2026-03-31
GET /api/v1/reports/cash-flow?date_from=2026-01-01&date_to=2026-03-31&grouping=month
GET /api/v1/reports/pending?scope=all&page_size=6&as_of=2026-03-15
GET /api/v1/reports/vat?year=2026
```

Empty results contain real zero totals, zero-filled cash buckets, empty categories/pending items and four zero VAT quarters. A genuine zero net with activity is displayed as zero, not hidden behind an empty-state marker. Failed requests instead show unavailable/loading states; old totals are hidden while a replacement period loads.

## Dashboard and Reports behavior

The shared selector supports This month, Last month, This quarter, This year, Year to date and Custom range. This year uses the full calendar year; Year to date ends today. The 6/12-month shortcuts run from the first day of the earliest month through today. Dashboard cash-flow shortcuts change the **shared** period, so KPIs, category breakdown and cash chart stay aligned. Custom dates are applied explicitly.

Upcoming payments deliberately show **all outstanding EUR movements**, independent of the period selector, so overdue entries outside the selected month remain visible. The label states that scope. Its View pending link opens Reports in all-outstanding mode; Reports otherwise defaults its pending section to the selected period and also provides a scope selector. Entry links open the saved Income/Expenses detail dialog using `#entry=<uuid>`.

Reports adds actual and expected financial overviews, monthly/weekly actual or expected cash-flow views, full income/expense category tables, annual recorded VAT quarters and paginated pending movements. Changing cash-flow grouping/basis or VAT year reloads only the affected endpoint. Data is refreshed on load/filter/retry; there is no live polling or historical snapshot store.

Recharts is the already-installed visualization library. Bar charts use recorded aggregate values, never invented interpolation. Exact amounts/shares in text, tooltips and expandable cash tables come from backend decimal strings; chart coordinates/axes are presentation numbers. Client-only reporting views avoid browser-calendar hydration differences. The existing sidebar and financial entry workflows are preserved.

## Verification and deployment

No migration, model change, dependency, mandatory service, environment variable or Compose/GHCR workflow change was required. Migration head remains 0002. Existing CI automatically picks up the new backend, browser and live reporting tests through its existing test commands.

Backend tests cover actual/expected separation, dates, month/week/quarter boundaries, leap day, timezone-independent grouping, soft deletion, currency exclusions, recorded VAT overrides, category percentages, empty data, precise arithmetic and bounded query counts. The live browser test creates persisted records and checks exact dashboard/report totals across status/date/currency differences. Responsive checks cover 1920, 1440, 1024, 768 and 390px.

Deploy matching web/API images through the existing main → GitHub Actions → GHCR → Portainer → orion-01 workflow after checks pass. Preserve the database volume and existing credentials. No report seeds or demo transactions are included in application startup. Backups remain normal deployment practice; no database reset is needed.

## Current limits

EUR only, no FX or account/bank balance. VAT is illustrative, without tax treatment or deductibility. Pending/status history reflects the current single payment-date field, so prior expected dates and point-in-time historical states cannot be reconstructed. Category names use current metadata. Queries read current data at request time; separate endpoints are not an immutable multi-report snapshot. Large ranges are bounded; exports, live refresh, recurring automation, OCR/Ollama, Sentinel and advanced accounting remain future work.
