import { error, json } from '@sveltejs/kit';
import { api } from '#lib/server/api.js';
import type { CounterpartyListItem } from '#lib/types.js';
import type { RequestHandler } from './$types';

/** Counterparty suggestions for the entry form's combobox. */
export const GET: RequestHandler = async (event) => {
  const q = (event.url.searchParams.get('q') ?? '').slice(0, 200);
  const result = await api<{ items: CounterpartyListItem[] }>(event, '/api/counterparties', {
    query: { q, limit: 8 }
  });
  if (!result.ok) error(result.unreachable ? 503 : result.status, result.message);
  return json(
    result.data.items.map(({ id, name, default_category_id, default_vat_rate_bp }) => ({
      id,
      name,
      default_category_id,
      default_vat_rate_bp
    }))
  );
};
