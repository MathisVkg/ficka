import { error, fail, redirect } from '@sveltejs/kit';
import { todayIso } from '#lib/dates.js';
import { api } from '#lib/server/api.js';
import { readEntryPayload } from '#lib/server/entry-form.js';
import type { Category, CompanySettings, Entry, VatRate } from '#lib/types.js';
import type { Actions, PageServerLoad } from './$types';

export const load: PageServerLoad = async (event) => {
  const [categories, rates, settings] = await Promise.all([
    api<Category[]>(event, '/api/categories'),
    api<VatRate[]>(event, '/api/vat-rates', { query: { on: todayIso() } }),
    api<CompanySettings>(event, '/api/company/settings')
  ]);
  if (!categories.ok) error(categories.unreachable ? 503 : categories.status, categories.message);
  return {
    categories: categories.data,
    rates: rates.ok ? rates.data : [],
    amountsIncludeVatDefault: settings.ok ? settings.data.amounts_include_vat_default : false
  };
};

export const actions: Actions = {
  default: async (event) => {
    const payload = readEntryPayload((await event.request.formData()).get('payload'));
    if (!payload) {
      return fail(400, { errors: {}, message: 'The form couldn’t be read. Reload the page.' });
    }
    const result = await api<Entry>(event, '/api/entries', { method: 'POST', body: payload });
    if (!result.ok) {
      return fail(result.status === 422 ? 422 : result.status, {
        errors: result.fields,
        message: result.code === 'validation_error' ? null : result.message
      });
    }
    redirect(303, `/entries/${result.data.id}?saved=1`);
  }
};
