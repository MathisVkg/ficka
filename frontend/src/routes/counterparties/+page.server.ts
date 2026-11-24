import { error } from '@sveltejs/kit';
import { api } from '#lib/server/api.js';
import type { CounterpartyListItem, CounterpartyRole } from '#lib/types.js';
import type { PageServerLoad } from './$types';

const PAGE_SIZE = 50;
const ROLES: CounterpartyRole[] = ['customer', 'supplier', 'both'];

export const load: PageServerLoad = async (event) => {
  const params = event.url.searchParams;
  const q = (params.get('q') ?? '').trim();
  const roleParam = params.get('role') as CounterpartyRole | null;
  const role = roleParam && ROLES.includes(roleParam) ? roleParam : null;
  const pageParam = params.get('page');
  const page =
    pageParam && /^\d+$/.test(pageParam) && Number(pageParam) > 0 ? Number(pageParam) : 1;

  const result = await api<{ items: CounterpartyListItem[]; total: number }>(
    event,
    '/api/counterparties',
    { query: { q, role, limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE } }
  );
  if (!result.ok) error(result.unreachable ? 503 : result.status, result.message);
  return { list: result.data, filters: { q, role, page }, pageSize: PAGE_SIZE };
};
