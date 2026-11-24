/**
 * Money and VAT for the live preview in the entry form. Integers only: amounts in cents,
 * rates in basis points. The arithmetic mirrors `backend/app/services/vat.py` exactly and
 * runs the same test vectors; the server's result is authoritative.
 *
 * Intermediate products use BigInt, so even 10 000 000 000,00 € × 21 % stays exact.
 */

export const MAX_AMOUNT_CENTS = 1_000_000_000_000;

export interface LineAmounts {
  netCents: number;
  vatCents: number;
  grossCents: number;
}

export class VatError extends Error {
  constructor(
    readonly field: 'net_cents' | 'gross_cents' | 'vat_rate_bp' | 'vat_cents',
    message: string
  ) {
    super(message);
  }
}

/** numerator / denominator rounded half up, for numerator >= 0 and denominator > 0. */
export function roundHalfUp(numerator: bigint, denominator: bigint): bigint {
  if (numerator < 0n || denominator <= 0n) {
    throw new RangeError('roundHalfUp expects numerator >= 0 and denominator > 0');
  }
  return (2n * numerator + denominator) / (2n * denominator);
}

export interface LineOptions {
  amountsIncludeVat: boolean;
  vatManual?: boolean;
  vatCents?: number | null;
}

/** Net, VAT and gross of one line. `amountCents` is the net, or the gross in gross mode. */
export function computeLine(
  amountCents: number,
  rateBp: number | null,
  { amountsIncludeVat, vatManual = false, vatCents = null }: LineOptions
): LineAmounts {
  const amountField = amountsIncludeVat ? 'gross_cents' : 'net_cents';
  if (!Number.isSafeInteger(amountCents) || amountCents < 0) {
    throw new VatError(amountField, 'Amounts can’t be negative.');
  }
  if (amountCents > MAX_AMOUNT_CENTS) throw new VatError(amountField, 'This amount is too large.');
  if (rateBp !== null && (!Number.isInteger(rateBp) || rateBp < 0 || rateBp > 10000)) {
    throw new VatError('vat_rate_bp', 'The VAT rate must be between 0 and 100 %.');
  }

  if (rateBp === null) {
    if (vatManual && vatCents) {
      throw new VatError('vat_cents', 'A line without a VAT rate can’t have VAT.');
    }
    return { netCents: amountCents, vatCents: 0, grossCents: amountCents };
  }

  if (vatManual) {
    if (vatCents === null || vatCents === undefined) {
      throw new VatError('vat_cents', 'Enter the VAT amount.');
    }
    if (vatCents < 0) throw new VatError('vat_cents', 'The VAT amount can’t be negative.');
    if (amountsIncludeVat) {
      if (vatCents > amountCents) {
        throw new VatError('vat_cents', 'The VAT can’t be more than the total amount.');
      }
      return { netCents: amountCents - vatCents, vatCents, grossCents: amountCents };
    }
    if (vatCents > MAX_AMOUNT_CENTS) throw new VatError('vat_cents', 'This amount is too large.');
    return { netCents: amountCents, vatCents, grossCents: amountCents + vatCents };
  }

  const amount = BigInt(amountCents);
  const rate = BigInt(rateBp);
  if (amountsIncludeVat) {
    const net = Number(roundHalfUp(amount * 10000n, 10000n + rate));
    return { netCents: net, vatCents: amountCents - net, grossCents: amountCents };
  }
  const vat = Number(roundHalfUp(amount * rate, 10000n));
  return { netCents: amountCents, vatCents: vat, grossCents: amountCents + vat };
}

// --- Parsing ---------------------------------------------------------------------------------

export type ParseResult = { ok: true; cents: number } | { ok: false; error: string };

/**
 * Parse a typed amount straight to cents, with string logic only (no float parsing).
 * Accepts `1512,50`, `1512.50`, `1 512,50`, `1.512,50` and `1,512.50`.
 * A single `.` or `,` is the decimal separator; with both, the last one is.
 * More than 2 decimals is refused (so `1.512` is refused rather than guessed).
 */
export function parseAmount(input: string): ParseResult {
  const value = input.replace(/[\s\u00a0\u202f]/g, '');
  if (value === '') return { ok: false, error: 'Enter an amount.' };
  if (/^[-−]/.test(value)) return { ok: false, error: 'Amounts can’t be negative.' };
  if (!/^[0-9.,]+$/.test(value)) {
    return { ok: false, error: 'Use digits, with a comma or a dot for the cents.' };
  }

  const lastDot = value.lastIndexOf('.');
  const lastComma = value.lastIndexOf(',');
  let decimalSeparator: string | null = null;
  let thousandsSeparator: string | null = null;
  if (lastDot >= 0 && lastComma >= 0) {
    decimalSeparator = lastDot > lastComma ? '.' : ',';
    thousandsSeparator = decimalSeparator === '.' ? ',' : '.';
  } else if (lastDot >= 0 || lastComma >= 0) {
    const separator = lastDot >= 0 ? '.' : ',';
    const count = value.split(separator).length - 1;
    if (count === 1) decimalSeparator = separator;
    else thousandsSeparator = separator;
  }

  let integerPart = value;
  let fraction = '';
  if (decimalSeparator) {
    const index = value.lastIndexOf(decimalSeparator);
    integerPart = value.slice(0, index);
    fraction = value.slice(index + 1);
    if (fraction.includes('.') || fraction.includes(',')) {
      return { ok: false, error: 'This amount isn’t valid.' };
    }
  }
  if (thousandsSeparator) {
    const groups = integerPart.split(thousandsSeparator);
    const valid =
      groups.length > 1 &&
      /^\d{1,3}$/.test(groups[0]) &&
      groups.slice(1).every((group) => /^\d{3}$/.test(group));
    if (!valid) return { ok: false, error: 'This amount isn’t valid.' };
    integerPart = groups.join('');
  }
  if (integerPart === '') integerPart = '0';
  if (!/^\d+$/.test(integerPart) || (decimalSeparator && fraction === '')) {
    return { ok: false, error: 'This amount isn’t valid.' };
  }
  if (fraction.length > 2) return { ok: false, error: 'Use at most 2 decimals.' };

  const digits = integerPart.replace(/^0+(?=\d)/, '');
  if (digits.length > 13) return { ok: false, error: 'This amount is too large.' };
  const cents = Number(digits) * 100 + Number(fraction.padEnd(2, '0'));
  if (cents > MAX_AMOUNT_CENTS) return { ok: false, error: 'This amount is too large.' };
  return { ok: true, cents };
}

// --- Formatting ------------------------------------------------------------------------------

const currency = new Intl.NumberFormat('fr-BE', { style: 'currency', currency: 'EUR' });

function decimalString(cents: number): `${number}` {
  const negative = cents < 0;
  const abs = Math.abs(cents);
  const euros = Math.trunc(abs / 100);
  const rest = abs - euros * 100;
  return `${negative ? '-' : ''}${euros}.${String(rest).padStart(2, '0')}` as `${number}`;
}

/** 151250 → "1 512,50 €" (formatted from an exact decimal string, no float division). */
export function formatCents(cents: number): string {
  return currency.format(decimalString(cents));
}

/** Income gets "+", expenses "−" (true minus sign). */
export function formatSigned(cents: number, direction: 'income' | 'expense'): string {
  return `${direction === 'income' ? '+' : '−'}${formatCents(Math.abs(cents))}`;
}

/** 151250 → "1512,50", the form an amount input shows for editing. */
export function centsToInput(cents: number | null | undefined): string {
  if (cents === null || cents === undefined) return '';
  return decimalString(cents).replace('.', ',');
}

/** Basis points → "21 %", "5,5 %". */
export function formatRate(rateBp: number | null): string {
  if (rateBp === null) return 'No VAT';
  const whole = Math.trunc(rateBp / 100);
  const rest = rateBp % 100;
  return rest === 0
    ? `${whole} %`
    : `${whole},${String(rest).padStart(2, '0').replace(/0$/, '')} %`;
}

/** "2026-11-14" → "14/11/2026" (string logic: no timezone surprises). */
export function formatDate(iso: string | null | undefined): string {
  if (!iso) return '';
  const [year, month, day] = iso.slice(0, 10).split('-');
  return `${day}/${month}/${year}`;
}
