/** Server side of the counterparty form: read the plain form fields into an API body. */
import { formString } from '#lib/forms.js';
import type { CounterpartyFormValues, CounterpartyRole } from '#lib/types.js';

export function readCounterpartyForm(form: FormData): {
  values: CounterpartyFormValues;
  body: Record<string, unknown>;
} {
  const roleRaw = formString(form, 'role');
  const role: CounterpartyRole =
    roleRaw === 'customer' || roleRaw === 'both' ? roleRaw : 'supplier';
  const values: CounterpartyFormValues = {
    name: formString(form, 'name'),
    role,
    vat_number: formString(form, 'vat_number'),
    ibans: form.getAll('ibans').filter((v): v is string => typeof v === 'string'),
    default_category_id: formString(form, 'default_category_id'),
    default_vat_rate_bp: formString(form, 'default_vat_rate_bp'),
    notes: formString(form, 'notes')
  };
  const asId = (v: string) => (/^\d+$/.test(v) ? Number(v) : null);
  return {
    values,
    body: {
      name: values.name,
      role,
      vat_number: values.vat_number.trim() || null,
      ibans: values.ibans.map((iban) => iban.trim()).filter(Boolean),
      default_category_id: asId(values.default_category_id),
      default_vat_rate_bp: asId(values.default_vat_rate_bp),
      notes: values.notes.trim() || null
    }
  };
}

/**
 * The API reports IBAN errors by position in the list it received (blank rows removed);
 * map them back to the rows the user sees.
 */
export function mapIbanErrors(
  fields: Record<string, string>,
  submitted: string[]
): Record<string, string> {
  const visibleIndex = submitted.map((v, i) => (v.trim() ? i : -1)).filter((i) => i >= 0);
  const mapped: Record<string, string> = {};
  for (const [key, message] of Object.entries(fields)) {
    const match = /^ibans\.(\d+)$/.exec(key);
    mapped[match ? `ibans.${visibleIndex[Number(match[1])] ?? match[1]}` : key] = message;
  }
  return mapped;
}
