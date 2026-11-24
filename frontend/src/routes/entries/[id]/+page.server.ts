import { error, fail, redirect } from '@sveltejs/kit';
import { formString } from '#lib/forms.js';
import { isIsoDate } from '#lib/dates.js';
import { parseAmount } from '#lib/money.js';
import { api } from '#lib/server/api.js';
import { readEntryPayload } from '#lib/server/entry-form.js';
import type { Category, CompanySettings, Entry, VatRate } from '#lib/types.js';
import type { Actions, PageServerLoad } from './$types';

function entryId(raw: string): number {
  if (!/^\d+$/.test(raw)) error(404, 'This entry doesn’t exist.');
  return Number(raw);
}

export const load: PageServerLoad = async (event) => {
  const id = entryId(event.params.id);
  const entry = await api<Entry>(event, `/api/entries/${id}`);
  if (!entry.ok) error(entry.unreachable ? 503 : entry.status, entry.message);
  const [categories, rates, settings] = await Promise.all([
    api<Category[]>(event, '/api/categories'),
    api<VatRate[]>(event, '/api/vat-rates', { query: { on: entry.data.invoice_date } }),
    api<CompanySettings>(event, '/api/company/settings')
  ]);
  return {
    entry: entry.data,
    categories: categories.ok ? categories.data : [],
    rates: rates.ok ? rates.data : [],
    amountsIncludeVatDefault: settings.ok ? settings.data.amounts_include_vat_default : false
  };
};

export const actions: Actions = {
  save: async (event) => {
    const id = entryId(event.params.id);
    const payload = readEntryPayload((await event.request.formData()).get('payload'));
    if (!payload) {
      return fail(400, { errors: {}, message: 'The form couldn’t be read. Reload the page.' });
    }
    const body = { ...payload };
    delete body.paid_on; // payments are recorded separately on an existing entry
    const result = await api<Entry>(event, `/api/entries/${id}`, { method: 'PUT', body });
    if (!result.ok) {
      return fail(result.status, {
        errors: result.fields,
        message: result.code === 'validation_error' ? null : result.message
      });
    }
    redirect(303, `/entries/${id}?saved=1`);
  },

  confirm: async (event) => {
    const id = entryId(event.params.id);
    const result = await api<Entry>(event, `/api/entries/${id}/confirm`, { method: 'POST' });
    if (!result.ok) return fail(result.status, { action: 'confirm', message: result.message });
    redirect(303, `/entries/${id}?saved=1`);
  },

  delete: async (event) => {
    const id = entryId(event.params.id);
    const result = await api(event, `/api/entries/${id}`, { method: 'DELETE' });
    if (!result.ok) return fail(result.status, { action: 'delete', message: result.message });
    redirect(303, '/entries?deleted=1');
  },

  addPayment: async (event) => {
    const id = entryId(event.params.id);
    const form = await event.request.formData();
    const paidOn = formString(form, 'paid_on');
    const amountText = formString(form, 'amount');
    const note = formString(form, 'note').trim();
    const errors: Record<string, string> = {};
    if (!isIsoDate(paidOn)) errors.paid_on = 'Enter the payment date.';
    const amount = parseAmount(amountText);
    if (!amount.ok) errors.amount_cents = amount.error;
    else if (amount.cents === 0) errors.amount_cents = 'Enter an amount above zero.';
    const values = { paid_on: paidOn, amount: amountText, note };
    if (Object.keys(errors).length > 0 || !amount.ok) {
      return fail(400, { action: 'addPayment', payment: { errors, values } });
    }
    const result = await api<Entry>(event, `/api/entries/${id}/payments`, {
      method: 'POST',
      body: { paid_on: paidOn, amount_cents: amount.cents, note: note || null }
    });
    if (!result.ok) {
      return fail(result.status, {
        action: 'addPayment',
        payment: {
          errors: Object.keys(result.fields).length ? result.fields : { form: result.message },
          values
        }
      });
    }
    return { action: 'addPayment', paymentAdded: true };
  },

  deletePayment: async (event) => {
    const form = await event.request.formData();
    const paymentId = formString(form, 'payment_id');
    if (!/^\d+$/.test(paymentId))
      return fail(400, { action: 'deletePayment', message: 'Unknown payment.' });
    const result = await api(event, `/api/payments/${paymentId}`, { method: 'DELETE' });
    if (!result.ok)
      return fail(result.status, { action: 'deletePayment', message: result.message });
    return { action: 'deletePayment' };
  }
};
