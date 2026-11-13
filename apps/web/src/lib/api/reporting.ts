"use client";
import { useEffect, useState } from "react";
import Decimal from "decimal.js";
import { api, today } from "@/lib/api/financial";
export type Period = { preset: string; start: string; end: string };
export type Meta = {
  currency: "EUR";
  date_from: string;
  date_to: string;
  date_basis: "payment_date" | "entry_date";
  non_eur_excluded_count: number;
};
export type Totals = {
  income: string;
  expenses: string;
  net: string;
  entry_count: number;
};
export type Summary = Meta & {
  actual: Totals;
  expected: Totals;
  vat: {
    output: string;
    input: string;
    difference: string;
    entry_count: number;
    date_basis: "entry_date";
    non_eur_excluded_count: number;
  };
};
export type CashBucket = {
  bucket_start: string;
  date_from: string;
  date_to: string;
  income: string;
  expenses: string;
  net: string;
  entry_count: number;
};
export type CashFlow = Meta & {
  grouping: "month" | "week";
  basis: "actual" | "expected";
  entry_count: number;
  items: CashBucket[];
};
export type CategoryTotal = {
  id: string | null;
  name: string;
  color: string | null;
  active: boolean | null;
  amount: string;
  percentage: string;
  entry_count: number;
};
export type Categories = Meta & {
  type: "income" | "expense";
  total: string;
  entry_count: number;
  items: CategoryTotal[];
};
export type PendingItem = {
  id: string;
  type: "income" | "expense";
  title: string;
  amount: string;
  currency: "EUR";
  payment_date: string;
  overdue: boolean;
};
export type Pending = {
  currency: "EUR";
  scope: "period" | "all";
  date_from: string | null;
  date_to: string | null;
  as_of: string;
  income: string;
  expenses: string;
  net: string;
  total: number;
  overdue_count: number;
  non_eur_excluded_count: number;
  page: number;
  page_size: number;
  items: PendingItem[];
};
export type VatQuarter = {
  quarter: number;
  date_from: string;
  date_to: string;
  output: string;
  input: string;
  difference: string;
  entry_count: number;
};
export type Vat = Meta & {
  year: number;
  output: string;
  input: string;
  difference: string;
  entry_count: number;
  quarters: VatQuarter[];
};
export function useReport<T>(path: string) {
  const [revision, setRevision] = useState(0);
  const [result, setResult] = useState<{
    key: string;
    data: T | null;
    error: string;
  }>({ key: "", data: null, error: "" });
  const key = path + "#" + revision;
  useEffect(() => {
    const controller = new AbortController();
    api<T>("reports/" + path, { signal: controller.signal }).then(
      (data) => {
        if (!controller.signal.aborted) setResult({ key, data, error: "" });
      },
      (error) => {
        if (!controller.signal.aborted)
          setResult({
            key,
            data: null,
            error:
              error instanceof Error ? error.message : "Report unavailable",
          });
      },
    );
    return () => controller.abort();
  }, [path, key]);
  return {
    data: result.key === key ? result.data : null,
    error: result.key === key ? result.error : "",
    loading: result.key !== key,
    reload: () => setRevision((value) => value + 1),
  };
}
function iso(date: Date) {
  return [
    date.getFullYear(),
    String(date.getMonth() + 1).padStart(2, "0"),
    String(date.getDate()).padStart(2, "0"),
  ].join("-");
}
export function periodFor(preset: string, anchor = today()): Period {
  const now = new Date(anchor + "T12:00:00"),
    year = now.getFullYear(),
    month = now.getMonth();
  let start = new Date(year, month, 1, 12),
    end = new Date(year, month + 1, 0, 12);
  if (preset === "last-month") {
    start = new Date(year, month - 1, 1, 12);
    end = new Date(year, month, 0, 12);
  }
  if (preset === "quarter") {
    start = new Date(year, Math.floor(month / 3) * 3, 1, 12);
    end = new Date(year, Math.floor(month / 3) * 3 + 3, 0, 12);
  }
  if (preset === "year" || preset === "ytd") {
    start = new Date(year, 0, 1, 12);
    end = preset === "year" ? new Date(year, 11, 31, 12) : now;
  }
  if (preset === "6-months" || preset === "12-months") {
    start = new Date(year, month - (preset === "6-months" ? 5 : 11), 1, 12);
    end = now;
  }
  return { preset, start: iso(start), end: iso(end) };
}
export const periodQuery = (period: Period) =>
  new URLSearchParams({
    date_from: period.start,
    date_to: period.end,
  }).toString();
// Preserve exact Decimal strings for text. Numeric chart coordinates are presentation only.
export function eur(value: string) {
  try {
    const fixed = new Decimal(value).toFixed(2);
    const negative = fixed.startsWith("-");
    const [integer, fraction] = fixed.replace(/^-/, "").split(".");
    return (
      (negative ? "−" : "") +
      "€" +
      BigInt(integer).toLocaleString("en-GB") +
      "." +
      fraction
    );
  } catch {
    return "Unavailable";
  }
}
export function reportDate(value: string, short = false) {
  return new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "short",
    ...(short ? {} : { year: "numeric" as const }),
  }).format(new Date(value + "T12:00:00"));
}
const palette = [
  "#7250c9",
  "#25856a",
  "#d37569",
  "#b48d46",
  "#5685af",
  "#9a74a9",
  "#70a18d",
  "#9b8b7a",
];
export function categoryColor(category: CategoryTotal) {
  if (category.color) return category.color;
  const seed = category.id ?? "uncategorized";
  return palette[
    Array.from(seed).reduce((sum, c) => sum + c.charCodeAt(0), 0) %
      palette.length
  ];
}
