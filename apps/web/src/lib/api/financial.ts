export type EntryType = "income" | "expense";
export type EntryStatus = "draft" | "pending" | "paid";
export type Category = {
  id: string;
  name: string;
  type: EntryType;
  color: string | null;
  active: boolean;
};
export type EntryInput = {
  title: string;
  amount: string;
  currency: string;
  country: string;
  category_id: string | null;
  counterparty: string | null;
  entry_date: string;
  payment_date: string;
  status: EntryStatus;
  vat_rate: string;
  vat_amount: string | null;
  notes: string | null;
};
export type Entry = Omit<EntryInput, "vat_amount"> & {
  id: string;
  type: EntryType;
  vat_amount: string;
  vat_overridden: boolean;
  amount_excluding_vat: string;
  category: Category | null;
  created_at: string;
  updated_at: string;
};
export type EntryPage = {
  items: Entry[];
  total: number;
  page: number;
  page_size: number;
};
export class ApiError extends Error {
  constructor(
    message: string,
    public fields: Record<string, string> = {},
  ) {
    super(message);
  }
}
export async function api<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  let response: Response;
  try {
    response = await fetch("/api/v1/" + path, {
      ...options,
      cache: "no-store",
      headers: { "Content-Type": "application/json", ...options.headers },
    });
  } catch (error) {
    if (error instanceof Error && error.name === "AbortError") throw error;
    throw new ApiError(
      "Cannot reach Ficka. Check the connection and try again; your input is preserved.",
    );
  }
  if (!response.ok) {
    const data = await response.json().catch(() => null);
    throw new ApiError(
      data?.error?.fields?.form ??
        data?.error?.message ??
        "The request could not be completed. Please retry.",
      data?.error?.fields ?? {},
    );
  }
  return response.status === 204
    ? (undefined as T)
    : ((await response.json()) as T);
}
export const entryPath = (kind: EntryType) =>
  kind === "income" ? "income" : "expenses";
export const listEntries = (
  kind: EntryType,
  query: string,
  signal?: AbortSignal,
) => api<EntryPage>(entryPath(kind) + "?" + query, { signal });
export const listCategories = (kind?: EntryType, signal?: AbortSignal) =>
  api<Category[]>("categories" + (kind ? "?type=" + kind : ""), { signal });
export const saveEntry = (kind: EntryType, data: EntryInput, id?: string) =>
  api<Entry>(entryPath(kind) + (id ? "/" + id : ""), {
    method: id ? "PATCH" : "POST",
    body: JSON.stringify(data),
  });
export const removeEntry = (kind: EntryType, id: string) =>
  api<void>(entryPath(kind) + "/" + id, { method: "DELETE" });
export function today() {
  const d = new Date();
  return [
    d.getFullYear(),
    String(d.getMonth() + 1).padStart(2, "0"),
    String(d.getDate()).padStart(2, "0"),
  ].join("-");
}
export const statusLabel = (status: EntryStatus, kind: EntryType) =>
  status === "paid"
    ? kind === "income"
      ? "Received"
      : "Paid"
    : status === "pending"
      ? "Pending"
      : "Draft";
export const formatMoney = (amount: string, currency: string) =>
  new Intl.NumberFormat("en-BE", { style: "currency", currency }).format(
    Number(amount),
  );
export const formatDate = (value: string) =>
  new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(new Date(value + "T12:00:00"));
