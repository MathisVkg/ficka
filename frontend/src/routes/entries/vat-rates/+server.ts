import { error, json } from '@sveltejs/kit';
import { isIsoDate } from '#lib/dates.js';
import { api } from '#lib/server/api.js';
import type { VatRate } from '#lib/types.js';
import type { RequestHandler } from './$types';

/** The VAT rates valid on a date, for the entry form when the invoice date changes. */
export const GET: RequestHandler = async (event) => {
  const on = event.url.searchParams.get('on');
  if (!isIsoDate(on)) error(400, 'Give a date as ?on=YYYY-MM-DD.');
  const result = await api<VatRate[]>(event, '/api/vat-rates', { query: { on } });
  if (!result.ok) error(result.unreachable ? 503 : result.status, result.message);
  return json(result.data);
};
