"use client";
import {
  Children,
  cloneElement,
  isValidElement,
  useEffect,
  useId,
  useState,
} from "react";
import Decimal from "decimal.js";
import { Button } from "@/components/ui/button";
import { ConfirmDialog, Modal } from "@/components/ui/modal";
import {
  ApiError,
  Category,
  Entry,
  EntryStatus,
  EntryType,
  saveEntry,
  today,
} from "@/lib/api/financial";
type FormValues = {
  title: string;
  amount: string;
  category: string;
  status: EntryStatus;
  entryDate: string;
  paymentDate: string;
  counterparty: string;
  vatRate: string;
  vatOverride: string;
  notes: string;
  currency: string;
  country: string;
};
function initialValues(entry?: Entry, markPaid = false): FormValues {
  return {
    title: entry?.title ?? "",
    amount: entry?.amount ?? "",
    category: entry?.category_id ?? "",
    status: markPaid ? "paid" : (entry?.status ?? "draft"),
    entryDate: entry?.entry_date ?? today(),
    paymentDate: markPaid ? today() : (entry?.payment_date ?? today()),
    counterparty: entry?.counterparty ?? "",
    vatRate: entry ? new Decimal(entry.vat_rate).toString() : "0",
    vatOverride: entry?.vat_overridden ? entry.vat_amount : "",
    notes: entry?.notes ?? "",
    currency: entry?.currency ?? "EUR",
    country: entry?.country ?? "BE",
  };
}
function Field({
  label,
  required,
  error,
  children,
  wide = false,
}: {
  label: string;
  required?: boolean;
  error?: string;
  children: React.ReactNode;
  wide?: boolean;
}) {
  const errorId = useId();
  return (
    <label className={wide ? "form-field full-width" : "form-field"}>
      <span>
        {label}
        {required && <span aria-hidden="true"> *</span>}
      </span>
      {Children.map(children, (child) => {
        if (
          isValidElement<{
            "aria-invalid"?: boolean;
            "aria-describedby"?: string;
            required?: boolean;
          }>(child) &&
          ["input", "select", "textarea"].includes(String(child.type))
        ) {
          return cloneElement(child, {
            "aria-invalid": !!error,
            "aria-describedby": error ? errorId : undefined,
            required,
          });
        }
        return child;
      })}
      {error && (
        <small id={errorId} className="field-error">
          {error}
        </small>
      )}
    </label>
  );
}
export function EntryForm({
  kind,
  entry,
  markPaid,
  categories,
  onClose,
  onSaved,
}: {
  kind: EntryType;
  entry?: Entry;
  markPaid?: boolean;
  categories: Category[];
  onClose: () => void;
  onSaved: () => void;
}) {
  const [initial] = useState(() => initialValues(entry, markPaid));
  const [form, setForm] = useState(initial);
  const [linked, setLinked] = useState(!entry);
  const [busy, setBusy] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [message, setMessage] = useState("");
  const [discard, setDiscard] = useState(false);
  const [additional, setAdditional] = useState(!!entry);
  const dirty = JSON.stringify(form) !== JSON.stringify(initial);
  useEffect(() => {
    if (!dirty) return;
    const warn = (event: BeforeUnloadEvent) => {
      event.preventDefault();
    };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [dirty]);
  function change<K extends keyof FormValues>(key: K, value: FormValues[K]) {
    setForm((current) => ({ ...current, [key]: value }));
    setErrors((current) => ({ ...current, [key]: "" }));
  }
  const requestClose = () => {
    if (busy) return;
    if (dirty) setDiscard(true);
    else onClose();
  };
  let vat = "—",
    net = "—";
  try {
    const amount = new Decimal(form.amount);
    const rate = new Decimal(form.vatRate);
    const tax =
      form.vatOverride === ""
        ? amount
            .mul(rate)
            .div(new Decimal(100).plus(rate))
            .toDecimalPlaces(2, Decimal.ROUND_HALF_UP)
        : new Decimal(form.vatOverride);
    if (
      amount.lte(0) ||
      rate.lt(0) ||
      rate.gt(100) ||
      tax.lt(0) ||
      tax.gt(amount)
    )
      throw new Error("Invalid preview");
    vat = tax.toFixed(2);
    net = amount.minus(tax).toFixed(2);
  } catch {}
  function validate() {
    const result: Record<string, string> = {};
    if (!form.title.trim()) result.title = "Enter a title.";
    if (
      !/^\d+(\.\d{1,2})?$/.test(form.amount) ||
      new Decimal(form.amount || 0).lte(0) ||
      new Decimal(form.amount || 0).gt("999999999999.99")
    )
      result.amount = "Enter a positive amount, up to two decimal places.";
    if (
      !/^\d+(\.\d{1,4})?$/.test(form.vatRate) ||
      new Decimal(form.vatRate || 0).gt(100)
    )
      result.vatRate =
        "Enter a VAT rate from 0 to 100, up to four decimal places.";
    if (
      form.vatOverride !== "" &&
      (!/^\d+(\.\d{1,2})?$/.test(form.vatOverride) ||
        (!result.amount &&
          new Decimal(form.vatOverride || 0).gt(form.amount || 0)))
    )
      result.vatOverride =
        "VAT must be between zero and the total, with up to two decimal places.";
    if (!form.entryDate) result.entryDate = "Choose an entry date.";
    if (!form.paymentDate) result.paymentDate = "Choose a payment date.";
    if (form.status === "paid" && form.paymentDate > today())
      result.paymentDate = "Actual payment dates cannot be in the future.";
    if (!/^[A-Z]{3}$/.test(form.currency))
      result.currency = "Use an uppercase ISO currency code.";
    if (!/^[A-Z]{2}$/.test(form.country))
      result.country = "Use an uppercase ISO country code.";
    return result;
  }
  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (busy) return;
    const invalid = validate();
    setErrors(invalid);
    setMessage("");
    if (Object.keys(invalid).length) {
      if (
        ["vatRate", "vatOverride", "currency", "country"].some(
          (key) => invalid[key],
        )
      )
        setAdditional(true);
      setMessage("Check the highlighted values.");
      return;
    }
    setBusy(true);
    try {
      await saveEntry(
        kind,
        {
          title: form.title.trim(),
          amount: new Decimal(form.amount).toFixed(2),
          category_id: form.category || null,
          status: form.status,
          entry_date: form.entryDate,
          payment_date: form.paymentDate,
          counterparty: form.counterparty.trim() || null,
          vat_rate: form.vatRate,
          vat_amount:
            form.vatOverride === ""
              ? null
              : new Decimal(form.vatOverride).toFixed(2),
          notes: form.notes.trim() || null,
          currency: form.currency,
          country: form.country,
        },
        entry?.id,
      );
      onSaved();
    } catch (error) {
      setMessage(
        error instanceof Error ? error.message : "Save failed. Please retry.",
      );
      if (error instanceof ApiError) {
        if (
          ["vat_rate", "vat_amount", "currency", "country"].some(
            (key) => error.fields[key],
          )
        )
          setAdditional(true);
        const keys: Record<string, string> = {
          entry_date: "entryDate",
          payment_date: "paymentDate",
          vat_rate: "vatRate",
          vat_amount: "vatOverride",
          category_id: "category",
        };
        setErrors(
          Object.fromEntries(
            Object.entries(error.fields).map(([key, value]) => [
              keys[key] ?? key,
              value,
            ]),
          ),
        );
      }
    } finally {
      setBusy(false);
    }
  }
  const noun = kind === "income" ? "income" : "expense";
  return (
    <>
      <Modal
        title={
          markPaid
            ? kind === "income"
              ? "Confirm received income"
              : "Confirm paid expense"
            : (entry ? "Edit " : "New ") + noun
        }
        description={
          markPaid
            ? "Confirm or adjust the actual payment date before saving."
            : "Record a financial entry. Amounts include VAT; * indicates a required field."
        }
        onClose={requestClose}
        busy={busy}
      >
        <form className="modal-form" noValidate onSubmit={submit}>
          <div className="modal-body form-grid">
            {message && (
              <div role="alert" className="form-error full-width">
                {message}
              </div>
            )}
            <Field label="Title" required error={errors.title} wide>
              <input
                disabled={busy}
                name="title"
                autoComplete="off"
                value={form.title}
                maxLength={200}
                aria-invalid={!!errors.title}
                onChange={(e) => change("title", e.target.value)}
                placeholder={
                  kind === "income"
                    ? "e.g. Website design project"
                    : "e.g. Monthly software subscription"
                }
              />
            </Field>
            <Field label="Amount including VAT" required error={errors.amount}>
              <input
                disabled={busy}
                inputMode="decimal"
                value={form.amount}
                aria-invalid={!!errors.amount}
                onChange={(e) => change("amount", e.target.value)}
                placeholder="0.00"
              />
            </Field>
            <Field label="Category" error={errors.category}>
              <select
                disabled={busy}
                value={form.category}
                onChange={(e) => change("category", e.target.value)}
              >
                <option value="">Uncategorized</option>
                {categories
                  .filter((c) => c.active || c.id === form.category)
                  .map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                      {!c.active ? " (archived)" : ""}
                    </option>
                  ))}
              </select>
            </Field>
            <Field label="Status" required>
              <select
                disabled={busy}
                value={form.status}
                onChange={(e) =>
                  change("status", e.target.value as EntryStatus)
                }
              >
                <option value="draft">Draft</option>
                <option value="pending">Pending</option>
                <option value="paid">
                  {kind === "income" ? "Received" : "Paid"}
                </option>
              </select>
            </Field>
            <p className="field-hint">
              {form.status === "draft"
                ? "Drafts are excluded from financial calculations."
                : form.status === "pending"
                  ? "Expected money movement. Not part of actual cash flow."
                  : "Money has moved. Confirm the actual payment date."}
            </p>
            <Field label="Entry date" required error={errors.entryDate}>
              <input
                disabled={busy}
                type="date"
                value={form.entryDate}
                onChange={(e) => {
                  change("entryDate", e.target.value);
                  if (linked) change("paymentDate", e.target.value);
                }}
              />
            </Field>
            <div>
              <Field
                label={
                  form.status === "paid"
                    ? "Actual payment date"
                    : "Payment date"
                }
                required
                error={errors.paymentDate}
              >
                <input
                  disabled={busy}
                  type="date"
                  value={form.paymentDate}
                  onChange={(e) => {
                    change("paymentDate", e.target.value);
                    setLinked(false);
                  }}
                />
              </Field>
              <button
                type="button"
                className="text-link date-reset"
                disabled={busy}
                onClick={() => {
                  change("paymentDate", form.entryDate);
                  setLinked(true);
                }}
              >
                Match entry date
              </button>
              <small className="field-hint">
                {linked ? "Follows entry date" : "Independent date"}
              </small>
            </div>
            <div className="vat-preview full-width">
              <span>
                Excluding VAT{" "}
                <strong>
                  {net} {form.currency}
                </strong>
              </span>
              <span>
                VAT{" "}
                <strong>
                  {vat} {form.currency}
                </strong>
              </span>
            </div>
            <details
              className="additional-fields full-width"
              open={additional}
              onToggle={(event) => setAdditional(event.currentTarget.open)}
            >
              <summary>VAT and additional details</summary>
              <div className="form-grid">
                <Field label={kind === "income" ? "Customer" : "Supplier"}>
                  <input
                    disabled={busy}
                    value={form.counterparty}
                    maxLength={200}
                    onChange={(e) => change("counterparty", e.target.value)}
                  />
                </Field>
                <Field label="VAT preset">
                  <select
                    disabled={busy}
                    value={
                      ["0", "6", "12", "21"].includes(form.vatRate)
                        ? form.vatRate
                        : "custom"
                    }
                    onChange={(e) =>
                      change(
                        "vatRate",
                        e.target.value === "custom" ? "" : e.target.value,
                      )
                    }
                  >
                    <option value="0">No VAT · 0%</option>
                    <option value="6">Belgium · 6%</option>
                    <option value="12">Belgium · 12%</option>
                    <option value="21">Belgium · 21%</option>
                    <option value="custom">Custom rate</option>
                  </select>
                </Field>
                <Field label="VAT rate (%)" error={errors.vatRate}>
                  <input
                    disabled={busy}
                    inputMode="decimal"
                    value={form.vatRate}
                    onChange={(e) => change("vatRate", e.target.value)}
                  />
                </Field>
                <Field label="VAT amount override" error={errors.vatOverride}>
                  <input
                    disabled={busy}
                    inputMode="decimal"
                    value={form.vatOverride}
                    onChange={(e) => change("vatOverride", e.target.value)}
                    placeholder="Automatic"
                  />
                  <small className="field-hint">
                    Leave blank to calculate from the total.
                  </small>
                </Field>
                <Field label="Currency" error={errors.currency}>
                  <input
                    disabled={busy}
                    value={form.currency}
                    maxLength={3}
                    onChange={(e) =>
                      change("currency", e.target.value.toUpperCase())
                    }
                  />
                </Field>
                <Field label="Country" error={errors.country}>
                  <input
                    disabled={busy}
                    value={form.country}
                    maxLength={2}
                    onChange={(e) =>
                      change("country", e.target.value.toUpperCase())
                    }
                  />
                  <small className="field-hint">
                    BE = Belgium. Rates are suggestions, not tax advice.
                  </small>
                </Field>
                <Field label="Notes" wide>
                  <textarea
                    disabled={busy}
                    value={form.notes}
                    maxLength={5000}
                    rows={3}
                    onChange={(e) => change("notes", e.target.value)}
                  />
                </Field>
                <p className="field-hint full-width">
                  Recorded VAT is not a tax return or a deduction calculation.
                  Deductibility is not assumed.
                </p>
              </div>
            </details>
          </div>
          <footer className="modal-footer">
            <Button
              type="button"
              variant="outline"
              onClick={requestClose}
              disabled={busy}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={busy}>
              {busy ? "Saving…" : entry ? "Save changes" : "Create " + noun}
            </Button>
          </footer>
        </form>
      </Modal>
      {discard && (
        <ConfirmDialog
          title="Discard unsaved changes?"
          description="Your changes have not been saved. Keep working to preserve them."
          confirmLabel="Discard changes"
          onCancel={() => setDiscard(false)}
          onConfirm={onClose}
        />
      )}
    </>
  );
}
