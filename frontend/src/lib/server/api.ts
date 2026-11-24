/**
 * The only way the SvelteKit server talks to the Ficka API.
 *
 * Every `load`, action and hook goes through `api()`: it sends the session token as
 * `Authorization: Bearer`, forwards the client IP for the login rate limit, applies a
 * timeout, parses JSON and turns failures into a typed result instead of throwing.
 * Nothing else may call `fetch(API_URL…)`.
 *
 * API errors have one shape (see backend `app/errors.py`):
 *   { "error": { "code": "validation_error", "message": "…", "fields": { "lines.0.net_cents": "…" } } }
 */
import { API_URL } from '$app/env/private';
import type { Cookies } from '@sveltejs/kit';
import { SESSION_COOKIE } from './session.js';

export type ApiErrorCode =
  | 'validation_error'
  | 'not_found'
  | 'conflict'
  | 'unauthorized'
  | 'rate_limited'
  | 'unreachable'
  | (string & {});

export interface ApiFailure {
  ok: false;
  /** HTTP status from the API, or 503 when the API couldn't be reached. */
  status: number;
  code: ApiErrorCode;
  message: string;
  /** Field errors keyed by dotted body path, e.g. `lines.0.vat_rate_bp`. */
  fields: Record<string, string>;
  /** Any extra data the API put in the error (e.g. usage counts on a conflict). */
  extra: Record<string, unknown>;
  /** True when the API didn't answer at all (down, timeout, network). */
  unreachable: boolean;
}

export type ApiResult<T> = { ok: true; status: number; data: T } | ApiFailure;

export interface ApiEvent {
  cookies: Cookies;
  getClientAddress: () => string;
}

export interface ApiOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
  body?: unknown;
  /** Query parameters; empty, null and undefined values are left out. */
  query?: Record<string, string | number | boolean | null | undefined>;
  /** Overrides the session cookie; pass `null` to send no token (login). */
  token?: string | null;
  timeoutMs?: number;
}

const DEFAULT_TIMEOUT_MS = 8000;

function clientAddress(event: ApiEvent): string | undefined {
  try {
    return event.getClientAddress();
  } catch {
    return undefined;
  }
}

function failure(payload: unknown, status: number): ApiFailure {
  const fallback = `The API answered with an error (${status}).`;
  if (payload && typeof payload === 'object' && 'error' in payload) {
    const error = (payload as { error: Record<string, unknown> }).error;
    const { code, message, fields, ...extra } = error;
    return {
      ok: false,
      status,
      code: typeof code === 'string' ? code : 'error',
      message: typeof message === 'string' ? message : fallback,
      fields: fields && typeof fields === 'object' ? (fields as Record<string, string>) : {},
      extra,
      unreachable: false
    };
  }
  return {
    ok: false,
    status,
    code: 'error',
    message: fallback,
    fields: {},
    extra: {},
    unreachable: false
  };
}

function withQuery(path: string, query: ApiOptions['query']): string {
  if (!query) return path;
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value !== undefined && value !== null && value !== '') params.set(key, String(value));
  }
  const search = params.toString();
  return search ? `${path}?${search}` : path;
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
    response = await fetch(`${API_URL}${withQuery(path, options.query)}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: AbortSignal.timeout(timeoutMs)
    });
  } catch {
    return {
      ok: false,
      status: 503,
      code: 'unreachable',
      message: 'Ficka cannot reach its server. Try again shortly.',
      fields: {},
      extra: {},
      unreachable: true
    };
  }

  const payload: unknown = response.status === 204 ? null : await response.json().catch(() => null);
  if (response.ok) {
    return { ok: true, status: response.status, data: payload as T };
  }
  return failure(payload, response.status);
}
