import { error } from '@sveltejs/kit';
import { isPeriod, periodRange, todayIso, type Period } from '#lib/dates.js';
import { api } from '#lib/server/api.js';
import type { Category, Counterparty, Direction, EntryList, PaymentStatus } from '#lib/types.js';
import type { PageServerLoad } from './$types';

const PAGE_SIZE = 50;

const PAYMENT_STATUSES: PaymentStatus[] = ['unpaid', 'partial', 'paid', 'overdue'];

function positiveInt(value: string | null): number | null {
  return value && /^\d+$/.test(value) && Number(value) > 0 ? Number(value) : null;
}

export const load: PageServerLoad = async (event) => {
  const params = event.url.searchParams;
  const directionParam = params.get('direction');
  const direction: Direction | null =
    directionParam === 'income' || directionParam === 'expense' ? directionParam : null;
  const periodParam = params.get('period');
  const period: Period = isPeriod(periodParam) ? periodParam : 'all';
  const range = periodRange(period, todayIso(), { from: params.get('from'), to: params.get('to') });
  const statusParam = params.get('payment_status') as PaymentStatus | null;
  const paymentStatus = statusParam && PAYMENT_STATUSES.includes(statusParam) ? statusParam : null;
  const categoryId = positiveInt(params.get('category_id'));
  const counterpartyId = positiveInt(params.get('counterparty_id'));
  const q = (params.get('q') ?? '').trim();
  const page = positiveInt(params.get('page')) ?? 1;

  const [list, categories, counterparty] = await Promise.all([
    api<EntryList>(event, '/api/entries', {
      query: {
        direction,
        payment_status: paymentStatus,
        category_id: categoryId,
        counterparty_id: counterpartyId,
        date_from: range.from,
        date_to: range.to,
        q,
        limit: PAGE_SIZE,
        offset: (page - 1) * PAGE_SIZE
      }
    }),
    api<Category[]>(event, '/api/categories'),
    counterpartyId
      ? api<Counterparty>(event, `/api/counterparties/${counterpartyId}`)
      : Promise.resolve(null)
  ]);

  if (!list.ok) error(list.unreachable ? 503 : list.status, list.message);

  return {
    list: list.data,
    categories: categories.ok ? categories.data : [],
    counterparty: counterparty?.ok
      ? { id: counterparty.data.id, name: counterparty.data.name }
      : null,
    filters: {
      direction,
      period,
      from: period === 'custom' ? range.from : null,
      to: period === 'custom' ? range.to : null,
      paymentStatus,
      categoryId,
      counterpartyId,
      q,
      page
    },
    pageSize: PAGE_SIZE
  };
};
