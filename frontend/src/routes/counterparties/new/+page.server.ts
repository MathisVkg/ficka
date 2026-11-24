import { fail, redirect } from '@sveltejs/kit';
import { todayIso } from '#lib/dates.js';
import { api } from '#lib/server/api.js';
import { mapIbanErrors, readCounterpartyForm } from '#lib/server/counterparty-form.js';
import type { Category, Counterparty, VatRate } from '#lib/types.js';
import type { Actions, PageServerLoad } from './$types';

export const load: PageServerLoad = async (event) => {
  const [categories, rates] = await Promise.all([
    api<Category[]>(event, '/api/categories'),
    api<VatRate[]>(event, '/api/vat-rates', { query: { on: todayIso() } })
  ]);
  return {
    categories: categories.ok ? categories.data : [],
    rates: rates.ok ? rates.data : []
  };
};

export const actions: Actions = {
  default: async (event) => {
    const { values, body } = readCounterpartyForm(await event.request.formData());
    const result = await api<Counterparty>(event, '/api/counterparties', { method: 'POST', body });
    if (!result.ok) {
      return fail(result.status, {
        values,
        errors: mapIbanErrors(result.fields, values.ibans),
        message: Object.keys(result.fields).length ? null : result.message
      });
    }
    redirect(303, `/counterparties/${result.data.id}?saved=1`);
  }
};
