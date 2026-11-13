"use client";
import Link from "next/link";
import { useState } from "react";
import {
  ArrowDownLeft,
  ArrowUpRight,
  ArrowRight,
  ChartNoAxesCombined,
  CircleDashed,
  CalendarDays,
  Repeat2,
  Plus,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { ConnectionStatus } from "@/components/layout/connection-status";
export function Dashboard() {
  const [period, setPeriod] = useState("This month");
  return (
    <>
      <div className="eyebrow">YOUR FINANCIAL OVERVIEW</div>
      <header className="page-header">
        <div>
          <h1>Dashboard</h1>
          <p>A little clarity. A better business day.</p>
        </div>
        <label className="period">
          <CalendarDays size={16} />
          <span className="sr-only">Reporting period</span>
          <select value={period} onChange={(e) => setPeriod(e.target.value)}>
            <option>This month</option>
            <option>Last month</option>
            <option>This year</option>
          </select>
        </label>
      </header>
      <ConnectionStatus />
      <section className="kpi-row" aria-label="Financial overview">
        {[
          ["Income", "income", ArrowDownLeft],
          ["Expenses", "expense", ArrowUpRight],
          ["Net cash flow", "primary", ChartNoAxesCombined],
          ["VAT estimate", "neutral", CircleDashed],
        ].map(([label, tone, Icon]) => {
          const KpiIcon = Icon as typeof ArrowDownLeft;
          return (
            <div className="kpi" key={String(label)}>
              <div className="kpi-label">
                <span>{String(label)}</span>
                <KpiIcon className={String(tone)} size={18} />
              </div>
              <div className="kpi-value" aria-label="No data">
                —
              </div>
              <p>
                {label === "VAT estimate"
                  ? "Available when VAT is configured"
                  : "No entries for this period"}
              </p>
            </div>
          );
        })}
      </section>
      <div className="dashboard-grid">
        <section className="panel cash-flow">
          <div className="section-heading">
            <h2>Cash flow</h2>
            <span>{period}</span>
          </div>
          <div className="chart-empty">
            <div className="chart-grid" aria-hidden="true" />
            <div className="empty-content">
              <ChartNoAxesCombined size={29} />
              <h3>Your story starts with an entry</h3>
              <p>
                Track income and expenses to see how money
                <br className="desktop-break" /> moves through your business.
              </p>
              <Button asChild size="sm">
                <Link href="/income">
                  <Plus size={15} />
                  Explore income
                </Link>
              </Button>
            </div>
          </div>
          <div className="chart-legend">
            <span>
              <i className="income-dot" />
              Income
            </span>
            <span>
              <i className="expense-dot" />
              Expenses
            </span>
          </div>
        </section>
        <section className="panel">
          <div className="section-heading">
            <h2>Expenses by category</h2>
          </div>
          <div className="category-empty">
            <div className="empty-ring">
              <CircleDashed size={56} strokeWidth={1} />
            </div>
            <h3>Make sense of your spending</h3>
            <p>
              Categories will appear here once
              <br />
              you record your first expense.
            </p>
            <Link className="text-link" href="/expenses">
              Explore expenses <ArrowRight size={14} />
            </Link>
          </div>
        </section>
      </div>
      <section className="payments">
        <div className="section-heading">
          <h2>Upcoming payments</h2>
          <Link className="text-link" href="/recurring">
            View recurring <ArrowRight size={14} />
          </Link>
        </div>
        <div className="payment-empty">
          <CalendarDays size={26} />
          <div>
            <h3>Nothing on the horizon yet</h3>
            <p>
              Upcoming recurring payments will appear here when scheduling is
              available.
            </p>
          </div>
          <span className="quiet-tag">No scheduled payments</span>
        </div>
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
        <Link className="text-link" href="/recurring">
          Recurring <ArrowRight size={14} />
        </Link>
      </aside>
      <footer className="page-footer">
        A fresh start. Your financial overview will grow with your business.
      </footer>
    </>
  );
}
