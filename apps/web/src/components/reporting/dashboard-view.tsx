"use client";
import Link from "next/link";
import { useState } from "react";
import { today } from "@/lib/api/financial";
import { Repeat2, ArrowRight } from "lucide-react";
import { ConnectionStatus } from "@/components/layout/connection-status";
import { PeriodSelector } from "@/components/reporting/period-selector";
import { CashFlowChart, ExpenseDonut } from "@/components/reporting/charts";
import {
  CurrencyNotice,
  PendingMovements,
  ReportError,
  SummaryKpis,
} from "@/components/reporting/shared";
import {
  CashFlow,
  Categories,
  Pending,
  Summary,
  periodFor,
  periodQuery,
  reportDate,
  useReport,
} from "@/lib/api/reporting";
export function DashboardView() {
  const [period, setPeriod] = useState(() => periodFor("month"));
  const query = periodQuery(period);
  const summary = useReport<Summary>("summary?" + query),
    flow = useReport<CashFlow>("cash-flow?" + query),
    categories = useReport<Categories>("expense-categories?" + query),
    pending = useReport<Pending>(
      "pending?scope=all&page_size=6&as_of=" + today(),
    );
  const error =
    summary.error || flow.error || categories.error || pending.error;
  const retry = () => {
    summary.reload();
    flow.reload();
    categories.reload();
    pending.reload();
  };
  return (
    <>
      <div className="eyebrow">YOUR FINANCIAL OVERVIEW</div>
      <header className="page-header report-header">
        <div>
          <h1>Dashboard</h1>
          <p>A little clarity. A better business day.</p>
        </div>
        <PeriodSelector
          key={period.preset + period.start + period.end}
          value={period}
          onChange={setPeriod}
        />
      </header>
      <div className="report-context">
        <span>
          {reportDate(period.start)} – {reportDate(period.end)}
        </span>
        <ConnectionStatus />
      </div>
      <ReportError message={error} retry={retry} />
      <SummaryKpis data={summary.data} loading={summary.loading} />
      <div className="overview-notes">
        <CurrencyNotice
          cash={summary.data?.non_eur_excluded_count}
          vat={summary.data?.vat.non_eur_excluded_count}
        />
        <p>
          Cash flow uses payment dates. VAT uses entry dates, includes Pending
          and Paid/Received, and is illustrative—not tax payable.
        </p>
      </div>
      <div className="report-dashboard-grid">
        <section className="report-section">
          <div className="section-heading chart-heading">
            <div>
              <h2>Cash flow</h2>
              <p>Actual received income and paid expenses</p>
            </div>
            <div
              className="chart-window-controls"
              aria-label="Cash-flow period shortcuts"
            >
              {[
                ["6-months", "6 months"],
                ["12-months", "12 months"],
                ["ytd", "Year to date"],
              ].map(([value, label]) => (
                <button
                  key={value}
                  aria-pressed={period.preset === value}
                  onClick={() => setPeriod(periodFor(value))}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
          <CashFlowChart
            data={flow.data}
            loading={flow.loading}
            error={flow.error}
          />
          <p className="report-note">
            Shortcuts update the shared reporting period above.
          </p>
        </section>
        <section className="report-section">
          <div className="section-heading">
            <div>
              <h2>Expenses by category</h2>
              <p>Paid expenses · selected payment dates</p>
            </div>
          </div>
          <ExpenseDonut
            data={categories.data}
            loading={categories.loading}
            error={categories.error}
          />
        </section>
      </div>
      <section className="report-section upcoming-section">
        <div className="section-heading">
          <div>
            <h2>Upcoming payments</h2>
            <p>
              All outstanding EUR movements · overdue first · independent of the
              period filter
            </p>
          </div>
          <Link
            href="/reports?pending=all#pending-movements"
            className="text-link"
          >
            View pending <ArrowRight size={14} />
          </Link>
        </div>
        <PendingMovements
          data={pending.data}
          loading={pending.loading}
          error={pending.error}
          compact
        />
        {pending.data && pending.data.total > 6 && (
          <p className="report-note">
            Showing the first 6 of {pending.data.total} outstanding EUR
            movements.
          </p>
        )}
      </section>
      <aside className="review-note">
        <Repeat2 size={19} />
        <div>
          <strong>A routine worth reviewing</strong>
          <p>
            Recurring proposals will need your approval before becoming
            financial entries.
          </p>
        </div>
        <Link href="/recurring" className="text-link">
          Recurring <ArrowRight size={14} />
        </Link>
      </aside>
      <footer className="page-footer">
        Drafts and deleted entries are excluded. No exchange rates or tax
        liability are inferred.
      </footer>
    </>
  );
}
