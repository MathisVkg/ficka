/** Server side of the entry form: read the JSON `payload` field and check its shape. */
import { isIsoDate } from '#lib/dates.js';
import type { EntryPayload } from '#lib/types.js';

function text(value: unknown, max = 2000): string | null {
  return typeof value === 'string' && value.trim() ? value.slice(0, max) : null;
}

function id(value: unknown): number | null {
  return typeof value === 'number' && Number.isSafeInteger(value) && value > 0 ? value : null;
}

function cents(value: unknown): number | undefined {
  return typeof value === 'number' && Number.isSafeInteger(value) ? value : undefined;
}

/** The payload, or null when it isn't the shape the form sends (tampered or broken). */
export function readEntryPayload(raw: FormDataEntryValue | null): EntryPayload | null {
  if (typeof raw !== 'string' || raw.length > 200_000) return null;
  let data: unknown;
  try {
    data = JSON.parse(raw);
  } catch {
    return null;
  }
  if (!data || typeof data !== 'object') return null;
  const d = data as Record<string, unknown>;
  if (d.direction !== 'income' && d.direction !== 'expense') return null;
  if (typeof d.invoice_date !== 'string' || !Array.isArray(d.lines)) return null;

  return {
    direction: d.direction,
    // The API validates dates and amounts; here we only pass known fields through.
    invoice_date: d.invoice_date,
    due_date: text(d.due_date, 10),
    counterparty_id: id(d.counterparty_id),
    category_id: id(d.category_id),
    description: text(d.description, 500),
    invoice_number: text(d.invoice_number, 100),
    structured_reference: text(d.structured_reference, 40),
    amounts_include_vat: d.amounts_include_vat === true,
    document_location: text(d.document_location),
    paid_on: isIsoDate(typeof d.paid_on === 'string' ? d.paid_on : null)
      ? (d.paid_on as string)
      : null,
    lines: d.lines.slice(0, 200).map((line: unknown) => {
      const l = (line ?? {}) as Record<string, unknown>;
      return {
        description: text(l.description, 500),
        net_cents: cents(l.net_cents),
        gross_cents: cents(l.gross_cents),
        vat_rate_bp: typeof l.vat_rate_bp === 'number' ? l.vat_rate_bp : null,
        vat_cents: cents(l.vat_cents),
        vat_manual: l.vat_manual === true
      };
    })
  };
}
