import { error, json } from '@sveltejs/kit';
import { api } from '#lib/server/api.js';
import type { Suggestion } from '#lib/types.js';
import type { RequestHandler } from './$types';

/** Category and VAT rate from the most recent similar entry, for the entry form. */
export const GET: RequestHandler = async (event) => {
  const params = event.url.searchParams;
  const direction = params.get('direction');
  if (direction !== 'income' && direction !== 'expense') error(400, 'Give a direction.');
  const counterparty = params.get('counterparty_id');
  const result = await api<Suggestion>(event, '/api/entries/suggestion', {
    query: {
      direction,
      counterparty_id: counterparty && /^\d+$/.test(counterparty) ? counterparty : null,
      description: (params.get('description') ?? '').slice(0, 500)
    }
  });
  if (!result.ok) error(result.unreachable ? 503 : result.status, result.message);
  return json(result.data);
};
