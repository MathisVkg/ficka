"use client";
import Link from "next/link";
import {
  ArrowDownLeft,
  ArrowUpRight,
  ChartNoAxesCombined,
  CircleDashed,
  ArrowRight,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Categories,
  Pending,
  Summary,
  Vat,
  eur,
  categoryColor,
  reportDate,
} from "@/lib/api/reporting";
export function ReportError({
  message,
  retry,
}: {
  message: string;
  retry: () => void;
}) {
  return message ? (
    <div role="alert" className="report-error">
      <span>{message}</span>
      <Button variant="outline" size="sm" onClick={retry}>
        Retry reports
      </Button>
    </div>
  ) : null;
}
export function EmptyReport({
  title,
  children,
  href,
}: {
  title: string;
  children: React.ReactNode;
  href?: string;
}) {
  return (
    <div className="report-empty">
      <ChartNoAxesCombined size={25} />
      <h3>{title}</h3>
      <p>{children}</p>
      {href && (
        <Link className="text-link" href={href}>
          View entries <ArrowRight size={14} />
        </Link>
      )}
    </div>
  );
}
export function ReportState({
  loading,
  error,
}: {
  loading: boolean;
  error?: string;
}) {
  return (
    <div className="report-state" aria-live="polite">
      {loading
        ? "Loading financial data…"
        : error
          ? "This report is unavailable. Use Retry reports to try again."
          : "No report data available."}
    </div>
  );
}
export function SummaryKpis({
  data,
  loading,
  includeVat = true,
}: {
  data: Summary | null;
  loading: boolean;
  includeVat?: boolean;
}) {
  const items = [
    {
      key: "income",
      label: "Income",
      value: data?.actual.income,
      description: "Received · payment dates",
      Icon: ArrowDownLeft,
      tone: "income",
    },
    {
      key: "expenses",
      label: "Expenses",
      value: data?.actual.expenses,
      description: "Paid · payment dates",
      Icon: ArrowUpRight,
      tone: "expense",
    },
    {
      key: "net",
      label: "Net cash flow",
      value: data?.actual.net,
      description: "Actual income less paid expenses",
      Icon: ChartNoAxesCombined,
      tone: "primary",
    },
    ...(includeVat
      ? [
          {
            key: "vat",
            label: "VAT overview",
            value: data?.vat.difference,
            description: "Recorded difference · illustrative",
            Icon: CircleDashed,
            tone: "neutral",
          },
        ]
      : []),
  ];
  return (
    <section
      className={"kpi-row report-kpis " + (!includeVat ? "kpi-three" : "")}
      aria-label="Financial overview"
      aria-busy={loading}
    >
      {items.map(({ key, label, value, description, Icon, tone }) => (
        <div className="kpi" key={key} data-testid={"kpi-" + key}>
          <div className="kpi-label">
            <span>{label}</span>
            <Icon size={18} className={tone} />
          </div>
          <div className="kpi-value">
            {value !== undefined ? eur(value) : loading ? "…" : "—"}
          </div>
          <p>{description}</p>
        </div>
      ))}
    </section>
  );
}
export function CurrencyNotice({
  cash = 0,
  vat = 0,
}: {
  cash?: number;
  vat?: number;
}) {
  return (
    <p className="currency-notice">
      EUR reporting only · no currency conversion.
      {cash > 0 && (
        <span>
          {" "}
          {cash} non-EUR cash movement{cash === 1 ? "" : "s"} excluded.
        </span>
      )}
      {vat > 0 && (
        <span>
          {" "}
          {vat} non-EUR VAT entr{vat === 1 ? "y" : "ies"} excluded.
        </span>
      )}
    </p>
  );
}
export function CategoryTable({ data }: { data: Categories }) {
  return (
    <div className="report-table-scroll category-report-table">
      <table className="report-table">
        <caption className="sr-only">
          {data.type === "income" ? "Income" : "Expense"} category breakdown
        </caption>
        <thead>
          <tr>
            <th>Category</th>
            <th className="numeric">Amount</th>
            <th className="numeric">Share</th>
          </tr>
        </thead>
        <tbody>
          {data.items.map((category) => (
            <tr key={category.id ?? "none"}>
              <td>
                <span className="category-label">
                  <i style={{ backgroundColor: categoryColor(category) }} />
                  {category.name}
                  {category.active === false && <small>Archived</small>}
                </span>
                <div className="category-track">
                  <i
                    style={{
                      width: category.percentage + "%",
                      backgroundColor: categoryColor(category),
                    }}
                  />
                </div>
              </td>
              <td className="numeric">{eur(category.amount)}</td>
              <td className="numeric">{category.percentage}%</td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr>
            <th>Total {data.type === "income" ? "received" : "paid"}</th>
            <td className="numeric">{eur(data.total)}</td>
            <td className="numeric">
              {data.entry_count ? "100.00%" : "0.00%"}
            </td>
          </tr>
        </tfoot>
      </table>
    </div>
  );
}
export function PendingMovements({
  data,
  loading,
  error,
  compact = false,
  onPage,
}: {
  data: Pending | null;
  loading: boolean;
  error: string;
  compact?: boolean;
  onPage?: (page: number) => void;
}) {
  if (!data) return <ReportState loading={loading} error={error} />;
  return (
    <>
      {!compact && (
        <div className="expected-totals">
          <div>
            <span>Expected pending income</span>
            <strong className="income">{eur(data.income)}</strong>
          </div>
          <div>
            <span>Expected pending expenses</span>
            <strong className="expense">{eur(data.expenses)}</strong>
          </div>
          <p>
            Pending movements only; excluded from actual cash flow.{" "}
            {data.overdue_count} overdue.
          </p>
        </div>
      )}
      {data.non_eur_excluded_count > 0 && (
        <p className="currency-notice">
          {data.non_eur_excluded_count} non-EUR pending entries excluded. No FX
          conversion.
        </p>
      )}
      {data.items.length === 0 ? (
        <EmptyReport title="No pending EUR movements">
          Nothing outstanding{" "}
          {data.scope === "all"
            ? "in EUR"
            : "within the selected expected-payment dates"}
          .
        </EmptyReport>
      ) : (
        <ul className="pending-list">
          {data.items.map((item) => (
            <li key={item.id}>
              <span className={"movement-icon " + item.type}>
                {item.type === "income" ? (
                  <ArrowDownLeft size={17} />
                ) : (
                  <ArrowUpRight size={17} />
                )}
              </span>
              <div className="pending-title">
                <Link
                  href={
                    (item.type === "income" ? "/income" : "/expenses") +
                    "#entry=" +
                    item.id
                  }
                >
                  {item.title}
                </Link>
                <p>
                  <span>
                    {item.type === "income"
                      ? "Expected income"
                      : "Expected expense"}
                  </span>{" "}
                  · {reportDate(item.payment_date)}
                  {item.overdue && (
                    <span className="pending-overdue"> · Overdue</span>
                  )}
                </p>
              </div>
              <strong className={item.type}>
                {item.type === "income" ? "+" : "−"}
                {eur(item.amount)}
              </strong>
              <Link
                className="text-link pending-open"
                aria-label={"Open " + item.title}
                href={
                  (item.type === "income" ? "/income" : "/expenses") +
                  "#entry=" +
                  item.id
                }
              >
                <ArrowRight size={15} />
              </Link>
            </li>
          ))}
        </ul>
      )}
      {onPage && (
        <div className="pagination">
          <span>
            {data.total} pending · Page {data.page} of{" "}
            {Math.max(1, Math.ceil(data.total / data.page_size))}
          </span>
          <div>
            <Button
              variant="outline"
              size="sm"
              disabled={data.page <= 1}
              onClick={() => onPage(data.page - 1)}
            >
              Previous movements
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={data.page * data.page_size >= data.total}
              onClick={() => onPage(data.page + 1)}
            >
              Next movements
            </Button>
          </div>
        </div>
      )}
    </>
  );
}
export function VatTable({ data }: { data: Vat }) {
  return (
    <>
      <div className="report-table-scroll">
        <table className="report-table vat-table">
          <caption className="sr-only">
            Recorded VAT by quarter for {data.year}
          </caption>
          <thead>
            <tr>
              <th>Calendar quarter</th>
              <th className="numeric">
                Output VAT
                <br />
                <small>Income recorded</small>
              </th>
              <th className="numeric">
                Input VAT
                <br />
                <small>Expenses recorded</small>
              </th>
              <th className="numeric">
                Illustrative
                <br />
                difference
              </th>
            </tr>
          </thead>
          <tbody>
            {data.quarters.map((q) => (
              <tr key={q.quarter}>
                <td>
                  Q{q.quarter}
                  <small className="quarter-dates">
                    {reportDate(q.date_from, true)} –{" "}
                    {reportDate(q.date_to, true)}
                  </small>
                </td>
                <td className="numeric">{eur(q.output)}</td>
                <td className="numeric">{eur(q.input)}</td>
                <td className="numeric">{eur(q.difference)}</td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr>
              <th>{data.year} recorded total</th>
              <td className="numeric">{eur(data.output)}</td>
              <td className="numeric">{eur(data.input)}</td>
              <td className="numeric">{eur(data.difference)}</td>
            </tr>
          </tfoot>
        </table>
      </div>
      {data.entry_count === 0 && (
        <p className="report-note">
          No non-draft EUR entries recorded in {data.year}.
        </p>
      )}
      <CurrencyNotice vat={data.non_eur_excluded_count} />
    </>
  );
}
