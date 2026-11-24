import { error, redirect } from '@sveltejs/kit';
import type { Handle } from '@sveltejs/kit/hooks';
import { api } from '#lib/server/api.js';
import {
  clearSessionCookie,
  refreshSessionCookie,
  SESSION_COOKIE,
  type MeResponse
} from '#lib/server/session.js';

const PUBLIC_PATHS = new Set(['/login']);

/**
 * Resolves the session once per request, then guards every route:
 * - no user → redirect to /login?next=<path> (except public paths)
 * - user on /login → redirect to /
 * Static assets never reach this hook (served before it by Vite / adapter-node).
 */
export const handle: Handle = async ({ event, resolve }) => {
  event.locals.user = null;
  event.locals.company = null;

  if (event.cookies.get(SESSION_COOKIE)) {
    const me = await api<MeResponse>(event, '/api/auth/me');
    if (me.ok) {
      event.locals.user = me.data.user;
      event.locals.company = me.data.company;
      refreshSessionCookie(event.cookies, event.url, me.data.session_expires_at);
    } else if (me.status === 401) {
      clearSessionCookie(event.cookies, event.url);
    } else if (me.unreachable) {
      // Keep the cookie: the session may still be valid once the API is back.
      error(503, 'API unavailable. Ficka cannot reach its server; try again in a moment.');
    } else {
      error(502, `The API answered with an error (${me.status}). Try again in a moment.`);
    }
  }

  const path = event.url.pathname;
  const isPublic = PUBLIC_PATHS.has(path);

  if (!event.locals.user && !isPublic) {
    const next = `${path}${event.url.search}`;
    redirect(303, `/login?next=${encodeURIComponent(next)}`);
  }
  if (event.locals.user && path === '/login') {
    redirect(303, '/');
  }

  return resolve(event);
};
