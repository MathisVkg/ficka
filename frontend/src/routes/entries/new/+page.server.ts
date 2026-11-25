import { error, fail, redirect } from '@sveltejs/kit';
import { isIsoDate, todayIso } from '#lib/dates.js';
import { formString } from '#lib/forms.js';
import { api } from '#lib/server/api.js';
import { readEntryPayload } from '#lib/server/entry-form.js';
import { safeReturn, withParams } from '#lib/return-to.js';
import type { Category, Direction, Entry, VatRate } from '#lib/types.js';
import type { Actions, PageServerLoad } from './$types';

export const load: PageServerLoad = async (event) => {
  const params = event.url.searchParams;
  const directionParam = params.get('direction');
  const direction: Direction | null =
    directionParam === 'income' || directionParam === 'expense' ? directionParam : null;
  const dateParam = params.get('date');
  const date = isIsoDate(dateParam) ? dateParam : null;

  const [categories, rates] = await Promise.all([
    api<Category[]>(event, '/api/categories'),
    api<VatRate[]>(event, '/api/vat-rates', { query: { on: date ?? todayIso() } })
  ]);
  if (!categories.ok) error(categories.unreachable ? 503 : categories.status, categories.message);
  return {
    categories: categories.data,
    rates: rates.ok ? rates.data : [],
    initialDirection: direction,
    initialDate: date,
    /** Where Save and Cancel go back to (validated; /entries by default). */
    from: safeReturn(params.get('from')),
    // Changes on every "Save and add another", so the page re-mounts an empty form.
    formKey: `${event.url.search}`
  };
};

export const actions: Actions = {
  default: async (event) => {
    const form = await event.request.formData();
    const payload = readEntryPayload(form.get('payload'));
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
    const from = safeReturn(formString(form, 'from'));
    if (formString(form, 'then') === 'another') {
      redirect(
        303,
        withParams('/entries/new', {
          direction: payload.direction,
          date: payload.invoice_date,
          saved: result.data.id,
          from
        })
      );
    }
    // Back to the list the user came from, with the saved row highlighted.
    redirect(303, withParams(from, { saved: 1, highlight: result.data.id }));
  }
};
