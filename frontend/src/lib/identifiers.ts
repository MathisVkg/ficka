/** Display formats for Belgian identifiers (the API stores and validates them). */

/** "BE0123456749" → "BE 0123.456.749"; other countries "FR 12345678901". */
export function formatVatNumber(value: string | null | undefined): string {
  if (!value) return '';
  const be = /^BE(\d{4})(\d{3})(\d{3})$/.exec(value);
  if (be) return `BE ${be[1]}.${be[2]}.${be[3]}`;
  return value.length > 2 ? `${value.slice(0, 2)} ${value.slice(2)}` : value;
}

/** "BE71096123456769" → "BE71 0961 2345 6769". */
export function formatIban(value: string | null | undefined): string {
  if (!value) return '';
  return value.replace(/(.{4})(?=.)/g, '$1 ');
}

/** "090933755493" → "+++090/9337/55493+++". */
export function formatStructuredReference(value: string | null | undefined): string {
  if (!value) return '';
  if (!/^\d{12}$/.test(value)) return value;
  return `+++${value.slice(0, 3)}/${value.slice(3, 7)}/${value.slice(7)}+++`;
}
