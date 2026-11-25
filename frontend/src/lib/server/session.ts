import type { Cookies } from '@sveltejs/kit';
import { safeReturn } from '#lib/return-to.js';

export const SESSION_COOKIE = 'ficka_session';

/** The API's session lifetime (sliding, see docs/decisions.md). */
export const SESSION_LIFETIME_SECONDS = 30 * 24 * 60 * 60;

export interface SessionUser {
  id: number;
  email: string;
  display_name: string;
}

export interface SessionCompany {
  id: number;
  name: string;
}

export interface MeResponse {
  user: SessionUser;
  company: SessionCompany;
  session_expires_at: string;
}

export interface LoginResponse {
  token: string;
  expires_at: string;
  user: SessionUser;
}

/**
 * `Secure` follows the request protocol, so plain HTTP on the LAN works and HTTPS
 * behind a proxy gets a secure cookie. (Behind a proxy, adapter-node derives the
 * protocol from `ORIGIN`.)
 */
function cookieOptions(url: URL) {
  return {
    path: '/',
    httpOnly: true,
    sameSite: 'lax' as const,
    secure: url.protocol === 'https:'
  };
}

function secondsUntil(isoTimestamp: string): number {
  return Math.max(0, Math.floor((Date.parse(isoTimestamp) - Date.now()) / 1000));
}

export function setSessionCookie(cookies: Cookies, url: URL, token: string, expiresAt: string) {
  cookies.set(SESSION_COOKIE, token, { ...cookieOptions(url), maxAge: secondsUntil(expiresAt) });
}

/**
 * Keep the cookie's Max-Age in step with the sliding session: when the API has just
 * extended the session (less than an hour of the 30 days used), refresh the cookie.
 * That's at most one Set-Cookie every ~15 days.
 */
export function refreshSessionCookie(cookies: Cookies, url: URL, expiresAt: string) {
  const token = cookies.get(SESSION_COOKIE);
  if (token && secondsUntil(expiresAt) > SESSION_LIFETIME_SECONDS - 3600) {
    setSessionCookie(cookies, url, token, expiresAt);
  }
}

export function clearSessionCookie(cookies: Cookies, url: URL) {
  cookies.delete(SESSION_COOKIE, cookieOptions(url));
}

/** A safe post-login destination (same rule as the entry form's `from`), or `/`. */
export function safeNext(value: FormDataEntryValue | string | null | undefined): string {
  return safeReturn(value, '/');
}
