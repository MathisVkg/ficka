"use client";
import { useState } from "react";
import { today } from "@/lib/api/financial";
import { PeriodSelector } from "@/components/reporting/period-selector";
import { CashFlowChart } from "@/components/reporting/charts";
import {
  CategoryTable,
  CurrencyNotice,
  EmptyReport,
  PendingMovements,
  ReportError,
  ReportState,
  SummaryKpis,
  VatTable,
} from "@/components/reporting/shared";
import {
  CashFlow,
  Categories,
  Pending,
  Period,
  Summary,
  Vat,
  eur,
  periodFor,
  periodQuery,
  reportDate,
  useReport,
} from "@/lib/api/reporting";
export function ReportsView() {
  const [period, setPeriod] = useState(() => periodFor("month")),
    [grouping, setGrouping] = useState("month"),
    [basis, setBasis] = useState("actual");
  const [vatYear, setVatYear] = useState(String(new Date().getFullYear())),
    [page, setPage] = useState(1);
  const [pendingScope, setPendingScope] = useState(() =>
    new URLSearchParams(window.location.search).get("pending") === "all"
      ? "all"
      : "period",
  );
  function changePeriod(value: Period) {
    setPeriod(value);
    setVatYear(value.end.slice(0, 4));
    setPage(1);
  }
  const query = periodQuery(period),
    summary = useReport<Summary>("summary?" + query),
    flow = useReport<CashFlow>(
      "cash-flow?" + query + "&grouping=" + grouping + "&basis=" + basis,
    ),
    expenses = useReport<Categories>("expense-categories?" + query),
    income = useReport<Categories>("income-categories?" + query),
    pending = useReport<Pending>(
      "pending?" +
        (pendingScope === "all" ? "scope=all" : query) +
        "&page=" +
        page +
        "&page_size=10&as_of=" +
        today(),
    ),
    vat = useReport<Vat>("vat?year=" + encodeURIComponent(vatYear));
  const error =
    summary.error ||
    flow.error ||
    expenses.error ||
    income.error ||
    pending.error ||
    vat.error;
  const retry = () => {
    summary.reload();
    flow.reload();
    expenses.reload();
    income.reload();
    pending.reload();
    vat.reload();
  };
  return (
    <>
      <div className="eyebrow">YOUR BUSINESS, IN PERSPECTIVE</div>
      <header className="page-header report-header">
        <div>
          <h1>Reports</h1>
          <p>
            Understand actual cash movement, expected payments and recorded VAT.
          </p>
        </div>
        <PeriodSelector
          key={period.preset + period.start + period.end}
          value={period}
          onChange={changePeriod}
        />
      </header>
      <div className="report-range-label">
        {reportDate(period.start)} – {reportDate(period.end)} · actual and
        expected movements use payment dates
      </div>
      <ReportError message={error} retry={retry} />
      <section className="report-section">
        <h2>Financial overview</h2>
        <SummaryKpis
          data={summary.data}
          loading={summary.loading}
          includeVat={false}
        />
        <div className="expected-totals">
          <div>
            <span>Expected pending income</span>
            <strong className="income" data-testid="expected-income">
              {summary.data ? eur(summary.data.expected.income) : "—"}
            </strong>
          </div>
          <div>
            <span>Expected pending expenses</span>
            <strong className="expense" data-testid="expected-expenses">
              {summary.data ? eur(summary.data.expected.expenses) : "—"}
            </strong>
          </div>
          <p>
            Expected movements are separate from received income and paid
            expenses.
          </p>
        </div>
        <CurrencyNotice cash={summary.data?.non_eur_excluded_count} />
      </section>
      <section className="report-section report-divider">
        <div className="section-heading chart-heading">
          <div>
            <h2>Cash-flow evolution</h2>
            <p>
              {basis === "actual"
                ? "Actual cash movement by payment date"
                : "Pending projections by expected payment date"}
            </p>
          </div>
          <div className="report-chart-controls">
            <label>
              View
              <select
                aria-label="Cash-flow basis"
                value={basis}
                onChange={(e) => setBasis(e.target.value)}
              >
                <option value="actual">Actual · paid/received</option>
                <option value="expected">Expected · pending</option>
              </select>
            </label>
            <label>
              Group by
              <select
                aria-label="Cash-flow grouping"
                value={grouping}
                onChange={(e) => setGrouping(e.target.value)}
              >
                <option value="month">Monthly</option>
                <option value="week">Weekly · Monday start</option>
              </select>
            </label>
          </div>
        </div>
        <CashFlowChart
          data={flow.data}
          loading={flow.loading}
          error={flow.error}
          large
        />
      </section>
      <div className="report-breakdowns">
        <section
          id="expense-breakdown"
          className="report-section report-divider"
        >
          <div className="section-heading">
            <div>
              <h2>Expense breakdown</h2>
              <p>Paid EUR expenses · payment dates</p>
            </div>
          </div>
          {expenses.data ? (
            expenses.data.entry_count ? (
              <CategoryTable data={expenses.data} />
            ) : (
              <EmptyReport title="No paid EUR expenses" href="/expenses">
                No paid expenses match the selected dates.
              </EmptyReport>
            )
          ) : (
            <ReportState loading={expenses.loading} error={expenses.error} />
          )}
        </section>
        <section className="report-section report-divider">
          <div className="section-heading">
            <div>
              <h2>Income breakdown</h2>
              <p>Received EUR income · payment dates</p>
            </div>
          </div>
          {income.data ? (
            income.data.entry_count ? (
              <CategoryTable data={income.data} />
            ) : (
              <EmptyReport title="No received EUR income" href="/income">
                No received income matches the selected dates.
              </EmptyReport>
            )
          ) : (
            <ReportState loading={income.loading} error={income.error} />
          )}
        </section>
      </div>
      <section className="report-section report-divider">
        <div className="section-heading">
          <div>
            <h2>VAT overview</h2>
            <p>
              Recorded amounts by entry date · calendar quarters · Pending and
              Paid/Received
            </p>
          </div>
          <label className="vat-year">
            VAT reporting year
            <input
              aria-label="VAT reporting year"
              type="number"
              min={1900}
              max={2100}
              value={vatYear}
              onChange={(e) => setVatYear(e.target.value)}
            />
          </label>
        </div>
        <div className="vat-explanation">
          <strong>
            Illustrative recorded difference, not VAT payable or a refund.
          </strong>
          <p>
            Output VAT is recorded on income; input VAT is recorded on expenses.
            Expense VAT deductibility and Belgian tax-point rules are not
            modeled. Entry dates group these records for illustration, not legal
            tax periods. This annual view uses its own year selector.
          </p>
        </div>
        {vat.data ? (
          <VatTable data={vat.data} />
        ) : (
          <ReportState loading={vat.loading} error={vat.error} />
        )}
      </section>
      <section id="pending-movements" className="report-section report-divider">
        <div className="section-heading">
          <div>
            <h2>Pending movements</h2>
            <p>
              Expected payment dates within the selected period · not actual
              cash movement
            </p>
          </div>
          <label className="vat-year">
            Pending scope
            <select
              aria-label="Pending scope"
              value={pendingScope}
              onChange={(event) => {
                setPendingScope(event.target.value);
                setPage(1);
              }}
            >
              <option value="period">Selected period</option>
              <option value="all">All outstanding</option>
            </select>
          </label>
        </div>
        <PendingMovements
          data={pending.data}
          loading={pending.loading}
          error={pending.error}
          onPage={setPage}
        />
      </section>
      <footer className="page-footer">
        Drafts and deleted entries are excluded. Reports are EUR-only; no FX
        conversion, starting bank balance or advanced VAT accounting is modeled.
      </footer>
    </>
  );
}
