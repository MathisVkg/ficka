/**
 * Can an entry be shown in the simple form (one amount incl. VAT, Paid or not)?
 * If not, the form opens with "More details" expanded (and the lines editor when the
 * amounts need it), so nothing is ever hidden or lost.
 */
import type { Entry } from '#lib/types.js';

export type ComplexReason =
  | 'several_lines'
  | 'manual_vat'
  | 'net_mode'
  | 'partial_payment'
  | 'several_payments'
  | 'payment_date'
  | 'due_date_while_paid';

type EntryShape = Pick<
  Entry,
  | 'lines'
  | 'amounts_include_vat'
  | 'payments'
  | 'paid_cents'
  | 'total_gross_cents'
  | 'invoice_date'
  | 'due_date'
>;

export function complexReasons(entry: EntryShape): ComplexReason[] {
  const reasons: ComplexReason[] = [];
  if (entry.lines.length > 1) reasons.push('several_lines');
  if (entry.lines.some((line) => line.vat_manual)) reasons.push('manual_vat');
  if (!entry.amounts_include_vat) reasons.push('net_mode');
  if (entry.paid_cents > 0 && entry.paid_cents < entry.total_gross_cents) {
    reasons.push('partial_payment');
  }
  if (entry.payments.length > 1) reasons.push('several_payments');
  if (entry.payments.length === 1 && entry.payments[0].paid_on !== entry.invoice_date) {
    reasons.push('payment_date');
  }
  // A paid entry with a due date: the due date only shows under More details.
  if (entry.payments.length > 0 && entry.due_date) reasons.push('due_date_while_paid');
  return reasons;
}

/** Reasons that need the lines editor (the others only need More details open). */
export const LINE_REASONS: ComplexReason[] = ['several_lines', 'manual_vat', 'net_mode'];

/** Reasons that need the payments block (partial or several payments). */
export const PAYMENT_REASONS: ComplexReason[] = ['partial_payment', 'several_payments'];

export function canShowSimply(entry: EntryShape): boolean {
  return complexReasons(entry).length === 0;
}

export function needsLinesEditor(entry: EntryShape): boolean {
  return complexReasons(entry).some((reason) => LINE_REASONS.includes(reason));
}
