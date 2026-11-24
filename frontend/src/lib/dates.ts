/** Dates as ISO strings ('YYYY-MM-DD'), computed in Belgian time without Date arithmetic surprises. */

const TIME_ZONE = 'Europe/Brussels';

export function todayIso(now: Date = new Date()): string {
  // en-CA formats as YYYY-MM-DD.
  return new Intl.DateTimeFormat('en-CA', {
    timeZone: TIME_ZONE,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  }).format(now);
}

export function isIsoDate(value: string | null | undefined): value is string {
  if (!value || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const [y, m, d] = value.split('-').map(Number);
  const date = new Date(Date.UTC(y, m - 1, d));
  return date.getUTCFullYear() === y && date.getUTCMonth() === m - 1 && date.getUTCDate() === d;
}

function iso(year: number, month: number, day: number): string {
  return `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
}

function lastDay(year: number, month: number): number {
  return new Date(Date.UTC(year, month, 0)).getUTCDate();
}

export const PERIODS = [
  { value: 'all', label: 'All time' },
  { value: 'this-month', label: 'This month' },
  { value: 'last-month', label: 'Last month' },
  { value: 'this-quarter', label: 'This quarter' },
  { value: 'this-year', label: 'This year' },
  { value: 'custom', label: 'Custom' }
] as const;

export type Period = (typeof PERIODS)[number]['value'];

export function isPeriod(value: string | null): value is Period {
  return PERIODS.some((p) => p.value === value);
}

/** The [from, to] range of a period, or nulls for all time / incomplete custom ranges. */
export function periodRange(
  period: Period,
  today: string,
  custom: { from?: string | null; to?: string | null } = {}
): { from: string | null; to: string | null } {
  const [year, month] = today.split('-').map(Number);
  switch (period) {
    case 'this-month':
      return { from: iso(year, month, 1), to: iso(year, month, lastDay(year, month)) };
    case 'last-month': {
      const y = month === 1 ? year - 1 : year;
      const m = month === 1 ? 12 : month - 1;
      return { from: iso(y, m, 1), to: iso(y, m, lastDay(y, m)) };
    }
    case 'this-quarter': {
      const first = Math.floor((month - 1) / 3) * 3 + 1;
      return { from: iso(year, first, 1), to: iso(year, first + 2, lastDay(year, first + 2)) };
    }
    case 'this-year':
      return { from: iso(year, 1, 1), to: iso(year, 12, 31) };
    case 'custom':
      return {
        from: isIsoDate(custom.from) ? custom.from : null,
        to: isIsoDate(custom.to) ? custom.to : null
      };
    default:
      return { from: null, to: null };
  }
}
