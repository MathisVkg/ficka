"use client";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  PieChart,
  Pie,
  Cell,
} from "recharts";
import Link from "next/link";
import {
  CashFlow,
  CashBucket,
  Categories,
  CategoryTotal,
  categoryColor,
  eur,
  reportDate,
} from "@/lib/api/reporting";
import { EmptyReport, ReportState } from "@/components/reporting/shared";
const compactMoney = (value: number) =>
  new Intl.NumberFormat("en-BE", {
    style: "currency",
    currency: "EUR",
    notation: "compact",
    minimumFractionDigits: 0,
    maximumFractionDigits: 1,
  }).format(value);
export function CashFlowChart({
  data,
  loading,
  error,
  large = false,
}: {
  data: CashFlow | null;
  loading: boolean;
  error: string;
  large?: boolean;
}) {
  if (!data) return <ReportState loading={loading} error={error} />;
  if (!data.entry_count)
    return (
      <EmptyReport
        title={
          data.basis === "actual"
            ? "No actual cash movements in this period"
            : "No expected cash movements in this period"
        }
        href="/income"
      >
        {data.basis === "actual"
          ? "Received income and paid expenses appear here by payment date. Drafts and pending entries are excluded."
          : "Pending income and expenses appear here by expected payment date."}
      </EmptyReport>
    );
  const points = data.items.map((item) => ({
    ...item,
    incomePlot: Number(item.income),
    expensePlot: Number(item.expenses),
    label:
      data.grouping === "month"
        ? new Intl.DateTimeFormat("en-GB", {
            month: "short",
            year: "2-digit",
          }).format(new Date(item.bucket_start + "T12:00:00"))
        : reportDate(item.date_from, true),
  }));
  const valid = points.every(
    (p) => Number.isFinite(p.incomePlot) && Number.isFinite(p.expensePlot),
  );
  return (
    <>
      <div className="report-chart-legend" aria-label="Cash-flow legend">
        <span>
          <i className="income-dot" />
          Income
        </span>
        <span>
          <i className="expense-dot" />
          Expenses
        </span>
        <small>
          {data.basis === "actual" ? "Paid / received" : "Pending · expected"} ·
          EUR
        </small>
      </div>
      {valid ? (
        <div
          className={large ? "cash-report-chart large" : "cash-report-chart"}
          data-testid="cash-flow-chart"
        >
          <ResponsiveContainer width="100%" height="100%" minWidth={0}>
            <BarChart
              data={points}
              margin={{ top: 12, right: 6, bottom: 0, left: 0 }}
              accessibilityLayer
            >
              <CartesianGrid vertical={false} stroke="#eeebf3" />
              <XAxis
                dataKey="label"
                axisLine={false}
                tickLine={false}
                tick={{ fontSize: 10, fill: "#938a9f" }}
                minTickGap={24}
                interval="preserveStartEnd"
              />
              <YAxis
                tickFormatter={compactMoney}
                width={66}
                axisLine={false}
                tickLine={false}
                tick={{ fontSize: 10, fill: "#938a9f" }}
              />
              <Tooltip
                cursor={{ fill: "#f5f1fb" }}
                content={({ active, payload }) => {
                  const point = payload?.[0]?.payload as CashBucket | undefined;
                  return active && point ? (
                    <div className="report-tooltip">
                      <strong>
                        {reportDate(point.date_from, true)} –{" "}
                        {reportDate(point.date_to, true)}
                      </strong>
                      <span>
                        Income <b>{eur(point.income)}</b>
                      </span>
                      <span>
                        Expenses <b>{eur(point.expenses)}</b>
                      </span>
                      <span>
                        Net <b>{eur(point.net)}</b>
                      </span>
                    </div>
                  ) : null;
                }}
              />
              <Bar
                dataKey="incomePlot"
                name="Income"
                fill="#25856a"
                radius={[2, 2, 0, 0]}
                maxBarSize={32}
                isAnimationActive={false}
              />
              <Bar
                dataKey="expensePlot"
                name="Expenses"
                fill="#d37569"
                radius={[2, 2, 0, 0]}
                maxBarSize={32}
                isAnimationActive={false}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <p className="report-note">
          These values exceed the chart display scale. Use the exact figures
          below.
        </p>
      )}
      <details className="exact-figures">
        <summary>View exact cash-flow figures</summary>
        <div className="report-table-scroll">
          <table className="report-table">
            <caption className="sr-only">Exact cash-flow totals</caption>
            <thead>
              <tr>
                <th>Period</th>
                <th className="numeric">Income</th>
                <th className="numeric">Expenses</th>
                <th className="numeric">Net</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((item) => (
                <tr key={item.bucket_start}>
                  <td>
                    {reportDate(item.date_from, true)} –{" "}
                    {reportDate(item.date_to, true)}
                  </td>
                  <td className="numeric">{eur(item.income)}</td>
                  <td className="numeric">{eur(item.expenses)}</td>
                  <td className="numeric">{eur(item.net)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </>
  );
}
export function ExpenseDonut({
  data,
  loading,
  error,
}: {
  data: Categories | null;
  loading: boolean;
  error: string;
}) {
  if (!data) return <ReportState loading={loading} error={error} />;
  if (!data.entry_count)
    return (
      <EmptyReport title="No paid EUR expenses in this period" href="/expenses">
        Paid expenses will be grouped by category, including uncategorized
        spending.
      </EmptyReport>
    );
  const points = data.items.map((c) => ({ ...c, value: Number(c.amount) }));
  return (
    <>
      <div className="category-total">
        <span>Total paid expenses</span>
        <strong>{eur(data.total)}</strong>
      </div>
      <div className="donut-breakdown">
        <div className="donut-visual" aria-hidden="true">
          <ResponsiveContainer width="100%" height={180} minWidth={0}>
            <PieChart>
              <Pie
                data={points}
                dataKey="value"
                nameKey="name"
                innerRadius="60%"
                outerRadius="88%"
                startAngle={90}
                endAngle={-270}
                stroke="white"
                strokeWidth={2}
                isAnimationActive={false}
              >
                {points.map((c) => (
                  <Cell key={c.id ?? "none"} fill={categoryColor(c)} />
                ))}
              </Pie>
              <Tooltip
                content={({ active, payload }) => {
                  const c = payload?.[0]?.payload as CategoryTotal | undefined;
                  return active && c ? (
                    <div className="report-tooltip">
                      <strong>{c.name}</strong>
                      <span>
                        {eur(c.amount)} · {c.percentage}%
                      </span>
                    </div>
                  ) : null;
                }}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
        <ol
          className="category-legend"
          aria-label="Expense category proportions"
        >
          {data.items.slice(0, 6).map((c) => (
            <li key={c.id ?? "none"}>
              <i style={{ backgroundColor: categoryColor(c) }} />
              <div>
                <span>{c.name}</span>
                <small>{c.percentage}%</small>
              </div>
              <strong>{eur(c.amount)}</strong>
            </li>
          ))}
        </ol>
      </div>
      {data.items.length > 6 && (
        <p className="report-note">
          Top 6 of {data.items.length} categories shown; the chart and total
          include every category.
        </p>
      )}
      <Link className="text-link" href="/reports#expense-breakdown">
        View full breakdown →
      </Link>
      <p className="sr-only">
        All category amounts and percentages are available in the Reports
        expense breakdown.
      </p>
    </>
  );
}
