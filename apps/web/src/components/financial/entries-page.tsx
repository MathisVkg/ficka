"use client";
import { useEffect, useState } from "react";
import {
  ArrowDownLeft,
  ArrowUpRight,
  Plus,
  Search,
  Pencil,
  Trash2,
  Check,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { ConfirmDialog, Modal } from "@/components/ui/modal";
import { EntryForm } from "@/components/financial/entry-form";
import {
  api,
  Category,
  Entry,
  EntryPage,
  EntryType,
  entryPath,
  formatDate,
  formatMoney,
  listCategories,
  listEntries,
  removeEntry,
  statusLabel,
  today,
} from "@/lib/api/financial";
export function EntriesPage({ kind }: { kind: EntryType }) {
  const noun = kind === "income" ? "income" : "expense";
  const [filters, setFilters] = useState({
    search: "",
    date_from: "",
    date_to: "",
    status: "",
    category_id: "",
    sorting: "date:desc",
  });
  const [page, setPage] = useState(1),
    [version, setVersion] = useState(0);
  const [data, setData] = useState<EntryPage>({
    items: [],
    total: 0,
    page: 1,
    page_size: 20,
  });
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true),
    [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [editor, setEditor] = useState<{
    entry?: Entry;
    markPaid?: boolean;
  } | null>(null);
  const [detail, setDetail] = useState<Entry | null>(null),
    [deleting, setDeleting] = useState<Entry | null>(null);
  const [deleteBusy, setDeleteBusy] = useState(false),
    [deleteError, setDeleteError] = useState("");
  const query = new URLSearchParams({
    page: String(page),
    page_size: "20",
    sort: filters.sorting.split(":")[0],
    direction: filters.sorting.split(":")[1],
    ...Object.fromEntries(
      Object.entries(filters).filter(
        ([key, value]) => key !== "sorting" && value !== "",
      ),
    ),
  }).toString();
  useEffect(() => {
    const controller = new AbortController();
    Promise.all([
      listEntries(kind, query, controller.signal),
      listCategories(kind, controller.signal),
    ]).then(
      ([entries, cats]) => {
        setData(entries);
        setCategories(cats);
        setError("");
        setLoading(false);
      },
      (error) => {
        if (!controller.signal.aborted) {
          setError(error.message);
          setLoading(false);
        }
      },
    );
    return () => controller.abort();
  }, [kind, query, version]);
  useEffect(() => {
    const controller = new AbortController();
    const openLinkedEntry = () => {
      const id = window.location.hash.match(/^#entry=([0-9a-f-]{36})$/i)?.[1];
      if (!id) return;
      api<Entry>(entryPath(kind) + "/" + id, {
        signal: controller.signal,
      }).then(
        (value) => {
          if (!controller.signal.aborted) setDetail(value);
        },
        (error) => {
          if (!controller.signal.aborted)
            setError(
              error instanceof Error ? error.message : "Cannot open entry",
            );
        },
      );
    };
    openLinkedEntry();
    window.addEventListener("hashchange", openLinkedEntry);
    return () => {
      controller.abort();
      window.removeEventListener("hashchange", openLinkedEntry);
    };
  }, [kind]);
  function refresh(message = "") {
    setNotice(message);
    setLoading(true);
    setVersion((v) => v + 1);
  }
  function filter(key: keyof typeof filters, value: string) {
    setFilters((current) => ({ ...current, [key]: value }));
    setPage(1);
    setLoading(true);
  }
  async function showDetail(entry: Entry) {
    try {
      setDetail(await api<Entry>(entryPath(kind) + "/" + entry.id));
    } catch (error) {
      setError(error instanceof Error ? error.message : "Cannot open entry");
    }
  }
  async function deleteConfirmed() {
    if (!deleting || deleteBusy) return;
    setDeleteBusy(true);
    try {
      await removeEntry(kind, deleting.id);
      setDeleting(null);
      if (data.items.length === 1 && page > 1) setPage(page - 1);
      refresh("Entry deleted. Its history is retained in the database.");
    } catch (error) {
      setDeleteError(error instanceof Error ? error.message : "Delete failed");
    } finally {
      setDeleteBusy(false);
    }
  }
  const Icon = kind === "income" ? ArrowDownLeft : ArrowUpRight;
  return (
    <>
      <div className="eyebrow">YOUR FINANCIAL ENTRIES</div>
      <header className="page-header financial-header">
        <div>
          <h1>{kind === "income" ? "Income" : "Expenses"}</h1>
          <p>
            {kind === "income"
              ? "Track what you earn, from first draft to received payment."
              : "Keep business spending clear, from first draft to paid expense."}
          </p>
        </div>
        <Button onClick={() => setEditor({})}>
          <Plus size={16} />
          New {noun}
        </Button>
      </header>
      {notice && (
        <div className="save-notice" role="status">
          {notice}
          <button className="text-link" onClick={() => setNotice("")}>
            Dismiss
          </button>
        </div>
      )}
      <div className="financial-toolbar" aria-label="Entry filters">
        <label className="search-field">
          <span>Search</span>
          <div>
            <Search size={16} />
            <input
              aria-label="Search entries"
              value={filters.search}
              placeholder="Title, counterparty or notes"
              onChange={(e) => filter("search", e.target.value)}
            />
          </div>
        </label>
        <label>
          <span>From</span>
          <input
            type="date"
            value={filters.date_from}
            onChange={(e) => filter("date_from", e.target.value)}
          />
        </label>
        <label>
          <span>To</span>
          <input
            type="date"
            value={filters.date_to}
            onChange={(e) => filter("date_to", e.target.value)}
          />
        </label>
        <label>
          <span>Status</span>
          <select
            value={filters.status}
            onChange={(e) => filter("status", e.target.value)}
          >
            <option value="">All statuses</option>
            <option value="draft">Draft</option>
            <option value="pending">Pending</option>
            <option value="paid">
              {kind === "income" ? "Received" : "Paid"}
            </option>
          </select>
        </label>
        <label>
          <span>Category</span>
          <select
            value={filters.category_id}
            onChange={(e) => filter("category_id", e.target.value)}
          >
            <option value="">All categories</option>
            {categories.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
                {c.active ? "" : " (archived)"}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span>Sort by</span>
          <select
            value={filters.sorting}
            onChange={(e) => filter("sorting", e.target.value)}
          >
            <option value="date:desc">Date · newest</option>
            <option value="date:asc">Date · oldest</option>
            <option value="amount:desc">Amount · highest</option>
            <option value="amount:asc">Amount · lowest</option>
            <option value="created_at:desc">Recently created</option>
            <option value="created_at:asc">First created</option>
          </select>
        </label>
      </div>
      <div className="table-summary">
        <span>
          {loading
            ? "Loading entries…"
            : data.total + (data.total === 1 ? " entry" : " entries")}
        </span>
        <button
          className="text-link"
          onClick={() => {
            setFilters({
              search: "",
              date_from: "",
              date_to: "",
              status: "",
              category_id: "",
              sorting: "date:desc",
            });
            setPage(1);
            refresh();
          }}
        >
          Clear filters
        </button>
      </div>
      {error ? (
        <div role="alert" className="table-message">
          <h2>Entries could not be loaded</h2>
          <p>{error}</p>
          <Button variant="outline" onClick={() => refresh()}>
            Retry
          </Button>
        </div>
      ) : loading ? (
        <div className="table-message" role="status">
          Loading your {noun} entries…
        </div>
      ) : data.items.length === 0 ? (
        <div className="table-message">
          <Icon size={32} className={kind} />
          <h2>
            {Object.values(filters).some((v) => v !== "" && v !== "date:desc")
              ? "No entries match these filters"
              : "A clear record starts here"}
          </h2>
          <p>
            {data.total > 0
              ? "Try another page or clear your filters."
              : "Create your first " +
                noun +
                ", or adjust the filters to see other entries."}
          </p>
          <Button variant="outline" onClick={() => setEditor({})}>
            New {noun}
          </Button>
        </div>
      ) : (
        <div className="table-scroll">
          <table className="financial-table">
            <caption className="sr-only">
              {kind === "income" ? "Income entries" : "Expense entries"}
            </caption>
            <thead>
              <tr>
                <th className="date-column">Date</th>
                <th>Title</th>
                <th className="optional-column">
                  {kind === "income" ? "Customer" : "Supplier"}
                </th>
                <th className="optional-column">Category</th>
                <th className="amount-column">Amount</th>
                <th className="status-column">Status</th>
                <th>
                  <span className="sr-only">Actions</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((entry) => (
                <tr key={entry.id}>
                  <td className="date-column">
                    {formatDate(entry.entry_date)}
                  </td>
                  <td>
                    <button
                      className="entry-title"
                      onClick={() => void showDetail(entry)}
                    >
                      {entry.title}
                    </button>
                    <div className="mobile-entry-meta">
                      {formatDate(entry.entry_date)} ·{" "}
                      {statusLabel(entry.status, kind)}
                    </div>
                    {entry.status === "pending" &&
                      entry.payment_date < today() && (
                        <span className="overdue-label">
                          Overdue · {formatDate(entry.payment_date)}
                        </span>
                      )}
                  </td>
                  <td className="optional-column">
                    {entry.counterparty || "—"}
                  </td>
                  <td className="optional-column">
                    <span className="category-label">
                      {entry.category?.color && (
                        <i style={{ backgroundColor: entry.category.color }} />
                      )}
                      {entry.category?.name ?? "Uncategorized"}
                      {entry.category && !entry.category.active && (
                        <small>Archived</small>
                      )}
                    </span>
                  </td>
                  <td className={"amount-column " + kind}>
                    {formatMoney(entry.amount, entry.currency)}
                  </td>
                  <td className="status-column">
                    <span className={"status-badge status-" + entry.status}>
                      {statusLabel(entry.status, kind)}
                    </span>
                  </td>
                  <td>
                    <div className="row-actions">
                      <button
                        className="icon-button"
                        aria-label={"Edit " + entry.title}
                        onClick={() => setEditor({ entry })}
                      >
                        <Pencil size={15} />
                      </button>
                      {entry.status !== "paid" && (
                        <button
                          className="icon-button quick-pay"
                          aria-label={
                            (kind === "income"
                              ? "Mark received: "
                              : "Mark paid: ") + entry.title
                          }
                          onClick={() => setEditor({ entry, markPaid: true })}
                        >
                          <Check size={16} />
                        </button>
                      )}
                      <button
                        className="icon-button"
                        aria-label={"Delete " + entry.title}
                        onClick={() => {
                          setDeleteError("");
                          setDeleting(entry);
                        }}
                      >
                        <Trash2 size={15} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <div className="pagination">
        <span>
          Page {page} of {Math.max(1, Math.ceil(data.total / data.page_size))}
        </span>
        <div>
          <Button
            variant="outline"
            size="sm"
            disabled={loading || page <= 1}
            onClick={() => {
              setPage(page - 1);
              setLoading(true);
            }}
          >
            Previous
          </Button>
          <Button
            variant="outline"
            size="sm"
            disabled={loading || page * data.page_size >= data.total}
            onClick={() => {
              setPage(page + 1);
              setLoading(true);
            }}
          >
            Next
          </Button>
        </div>
      </div>
      <p className="financial-footnote">
        Amounts include VAT. Drafts are excluded from calculations; pending
        entries are expected movements. Only{" "}
        {kind === "income" ? "received" : "paid"} entries represent actual cash
        movement.
      </p>
      {editor && (
        <EntryForm
          key={(editor.entry?.id ?? "new") + String(editor.markPaid)}
          kind={kind}
          entry={editor.entry}
          markPaid={editor.markPaid}
          categories={categories}
          onClose={() => setEditor(null)}
          onSaved={() => {
            setEditor(null);
            refresh("Entry saved successfully.");
          }}
        />
      )}
      {deleting && (
        <ConfirmDialog
          title={"Delete “" + deleting.title + "”?"}
          description="The entry will disappear from normal views and future calculations. Its record is retained in the database; restoring it is not yet available in the UI."
          confirmLabel="Delete entry"
          busy={deleteBusy}
          error={deleteError}
          onCancel={() => setDeleting(null)}
          onConfirm={() => void deleteConfirmed()}
        />
      )}
      {detail && (
        <Modal
          title={detail.title}
          description={
            statusLabel(detail.status, kind) +
            " · " +
            formatMoney(detail.amount, detail.currency)
          }
          onClose={() => setDetail(null)}
        >
          <div className="modal-body">
            <dl className="entry-details">
              {[
                ["Entry date", formatDate(detail.entry_date)],
                [
                  detail.status === "paid"
                    ? "Actual payment date"
                    : "Expected payment date",
                  formatDate(detail.payment_date),
                ],
                ["Category", detail.category?.name ?? "Uncategorized"],
                [
                  kind === "income" ? "Customer" : "Supplier",
                  detail.counterparty ?? "—",
                ],
                [
                  "Excluding VAT",
                  formatMoney(detail.amount_excluding_vat, detail.currency),
                ],
                [
                  "VAT",
                  formatMoney(detail.vat_amount, detail.currency) +
                    (detail.vat_overridden ? " (manual override)" : ""),
                ],
                ["VAT rate", Number(detail.vat_rate) + "%"],
                ["Country", detail.country],
                ["Created", new Date(detail.created_at).toLocaleString()],
                ["Updated", new Date(detail.updated_at).toLocaleString()],
              ].map(([label, value]) => (
                <div key={label}>
                  <dt>{label}</dt>
                  <dd>{value}</dd>
                </div>
              ))}
            </dl>
            <h3>Notes</h3>
            <p className="entry-notes">{detail.notes || "No notes added."}</p>
          </div>
          <footer className="modal-footer">
            <Button variant="outline" onClick={() => setDetail(null)}>
              Close
            </Button>
            <Button
              onClick={() => {
                setEditor({ entry: detail });
                setDetail(null);
              }}
            >
              Edit {noun}
            </Button>
          </footer>
        </Modal>
      )}
    </>
  );
}
