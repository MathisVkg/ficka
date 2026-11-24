import { error, json } from '@sveltejs/kit';
import { api } from '#lib/server/api.js';
import type { Counterparty, CounterpartyRole } from '#lib/types.js';
import type { RequestHandler } from './$types';

/**
 * Create a minimal counterparty (name only) from the entry form's combobox.
 * JSON only: a cross-site page can't send this without a CORS preflight, and the
 * session cookie is SameSite=Lax.
 */
export const POST: RequestHandler = async (event) => {
  if (!event.request.headers.get('content-type')?.includes('application/json')) {
    error(415, 'Send JSON.');
  }
  const body = (await event.request.json().catch(() => null)) as {
    name?: unknown;
    role?: unknown;
  } | null;
  const name = typeof body?.name === 'string' ? body.name.trim() : '';
  const role: CounterpartyRole =
    body?.role === 'customer' || body?.role === 'both' ? body.role : 'supplier';
  if (!name) error(422, 'Enter a name.');

  const result = await api<Counterparty>(event, '/api/counterparties', {
    method: 'POST',
    body: { name, role }
  });
  if (!result.ok) {
    return json({ message: result.message, fields: result.fields }, { status: result.status });
  }
  const { id, default_category_id, default_vat_rate_bp } = result.data;
  return json({ id, name: result.data.name, default_category_id, default_vat_rate_bp });
};
