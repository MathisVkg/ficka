/**
 * The only way the SvelteKit server talks to the Ficka API.
 *
 * Every `load`, action and hook goes through `api()`: it sends the session token as
 * `Authorization: Bearer`, forwards the client IP for the login rate limit, applies a
 * timeout, parses JSON and turns failures into a typed result instead of throwing.
 * Nothing else may call `fetch(API_URL…)`.
 */
import { API_URL } from '$app/env/private';
import type { Cookies } from '@sveltejs/kit';
import { SESSION_COOKIE } from './session.js';

export type ApiResult<T> =
  | { ok: true; status: number; data: T }
  | {
      ok: false;
      /** HTTP status from the API, or 503 when the API couldn't be reached. */
      status: number;
      message: string;
      /** True when the API didn't answer at all (down, timeout, network). */
      unreachable: boolean;
    };

export interface ApiEvent {
  cookies: Cookies;
  getClientAddress: () => string;
}

export interface ApiOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
  body?: unknown;
  /** Overrides the session cookie; pass `null` to send no token (login). */
  token?: string | null;
  timeoutMs?: number;
}

const DEFAULT_TIMEOUT_MS = 5000;

function clientAddress(event: ApiEvent): string | undefined {
  try {
    return event.getClientAddress();
  } catch {
    return undefined;
  }
}

function errorMessage(payload: unknown, status: number): string {
  if (payload && typeof payload === 'object' && 'detail' in payload) {
    const detail = payload.detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail) && detail.length > 0) {
      const first = detail[0] as { msg?: unknown };
      if (typeof first.msg === 'string') return first.msg;
    }
  }
  return `The API answered with an error (${status}).`;
}

export async function api<T = unknown>(
  event: ApiEvent,
  path: `/api/${string}`,
  options: ApiOptions = {}
): Promise<ApiResult<T>> {
  const { method = 'GET', body, timeoutMs = DEFAULT_TIMEOUT_MS } = options;
  const token = options.token === undefined ? event.cookies.get(SESSION_COOKIE) : options.token;

  const headers: Record<string, string> = { Accept: 'application/json' };
  if (token) headers.Authorization = `Bearer ${token}`;
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  const ip = clientAddress(event);
  if (ip) headers['X-Ficka-Client-IP'] = ip;

  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: AbortSignal.timeout(timeoutMs)
    });
  } catch {
    return { ok: false, status: 503, message: 'The API is unavailable.', unreachable: true };
  }

  const payload: unknown = response.status === 204 ? null : await response.json().catch(() => null);
  if (response.ok) {
    return { ok: true, status: response.status, data: payload as T };
  }
  return {
    ok: false,
    status: response.status,
    message: errorMessage(payload, response.status),
    unreachable: false
  };
}
