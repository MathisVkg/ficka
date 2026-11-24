import { error, fail, redirect } from '@sveltejs/kit';
import { todayIso } from '#lib/dates.js';
import { api } from '#lib/server/api.js';
import { mapIbanErrors, readCounterpartyForm } from '#lib/server/counterparty-form.js';
import type { Category, Counterparty, EntryList, VatRate } from '#lib/types.js';
import type { Actions, PageServerLoad } from './$types';

function counterpartyId(raw: string): number {
  if (!/^\d+$/.test(raw)) error(404, 'This counterparty doesn’t exist.');
  return Number(raw);
}

export const load: PageServerLoad = async (event) => {
  const id = counterpartyId(event.params.id);
  const [counterparty, categories, rates, entries] = await Promise.all([
    api<Counterparty>(event, `/api/counterparties/${id}`),
    api<Category[]>(event, '/api/categories'),
    api<VatRate[]>(event, '/api/vat-rates', { query: { on: todayIso() } }),
    // Every entry (any status) loses its link on delete: count them for the dialog.
    api<EntryList>(event, '/api/entries', { query: { counterparty_id: id, limit: 1 } })
  ]);
  if (!counterparty.ok) {
    error(counterparty.unreachable ? 503 : counterparty.status, counterparty.message);
  }
  return {
    counterparty: counterparty.data,
    categories: categories.ok ? categories.data : [],
    rates: rates.ok ? rates.data : [],
    linkedEntries: entries.ok ? entries.data.total : counterparty.data.stats.entries_count
  };
};

export const actions: Actions = {
  save: async (event) => {
    const id = counterpartyId(event.params.id);
    const { values, body } = readCounterpartyForm(await event.request.formData());
    const result = await api<Counterparty>(event, `/api/counterparties/${id}`, {
      method: 'PATCH',
      body
    });
    if (!result.ok) {
      return fail(result.status, {
        values,
        errors: mapIbanErrors(result.fields, values.ibans),
        message: Object.keys(result.fields).length ? null : result.message
      });
    }
    redirect(303, `/counterparties/${id}?saved=1`);
  },

  delete: async (event) => {
    const id = counterpartyId(event.params.id);
    const result = await api<{ detached_entries: number }>(event, `/api/counterparties/${id}`, {
      method: 'DELETE'
    });
    if (!result.ok) return fail(result.status, { deleteMessage: result.message });
    redirect(303, `/counterparties?deleted=${result.data.detached_entries}`);
  }
};
