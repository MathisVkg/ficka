/**
 * Where to go back to after a form: a same-site relative path, or a fallback.
 * Used for `next` after login and `from` on the entry form.
 */

/**
 * A safe destination: starts with `/` but not `//` or `/\`, stays on this site, and is
 * never /login (to avoid loops). Anything else becomes `fallback`.
 */
export function safeReturn(value: unknown, fallback = '/entries'): string {
  if (typeof value !== 'string' || !value.startsWith('/') || /^\/[/\\]/.test(value)) {
    return fallback;
  }
  try {
    const base = 'http://ficka.invalid';
    const target = new URL(value, base);
    if (target.origin !== base || target.pathname === '/login') return fallback;
    return `${target.pathname}${target.search}${target.hash}`;
  } catch {
    return fallback;
  }
}

/** A path with some query parameters set (string) or removed (null). */
export function withParams(path: string, params: Record<string, string | number | null>): string {
  const url = new URL(path, 'http://ficka.invalid');
  for (const [key, value] of Object.entries(params)) {
    if (value === null) url.searchParams.delete(key);
    else url.searchParams.set(key, String(value));
  }
  return `${url.pathname}${url.search}${url.hash}`;
}

/** Query parameters that only drive a toast or a highlight: never part of a list's URL. */
export const TRANSIENT_PARAMS = ['saved', 'highlight', 'deleted', 'marked'] as const;

/** The current page as a `from` value, without the transient parameters. */
export function currentAsFrom(url: { href: string }): string {
  const cleaned = new URL(url.href);
  for (const key of TRANSIENT_PARAMS) cleaned.searchParams.delete(key);
  return `${cleaned.pathname}${cleaned.search}`;
}
