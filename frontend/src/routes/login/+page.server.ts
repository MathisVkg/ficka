import { fail, redirect } from '@sveltejs/kit';
import { formString } from '#lib/forms.js';
import { api } from '#lib/server/api.js';
import { safeNext, setSessionCookie, type LoginResponse } from '#lib/server/session.js';
import type { Actions, PageServerLoad } from './$types';

const INCORRECT = 'Incorrect email or password.';
const TOO_MANY_ATTEMPTS = 'Too many attempts. Try again in a few minutes.';

export const load: PageServerLoad = ({ url }) => {
  return { next: safeNext(url.searchParams.get('next')) };
};

export const actions: Actions = {
  default: async (event) => {
    const form = await event.request.formData();
    const email = formString(form, 'email').trim();
    const password = formString(form, 'password');
    const next = safeNext(form.get('next'));

    if (!email || !password) {
      return fail(400, { email, message: 'Enter your email and password.' });
    }

    const result = await api<LoginResponse>(event, '/api/auth/login', {
      method: 'POST',
      body: { email, password },
      token: null
    });

    if (!result.ok) {
      if (result.status === 429) return fail(429, { email, message: TOO_MANY_ATTEMPTS });
      if (result.unreachable) {
        return fail(503, { email, message: 'Ficka cannot reach its server. Try again shortly.' });
      }
      // 401, and anything unexpected: never say which field is wrong.
      return fail(401, { email, message: INCORRECT });
    }

    setSessionCookie(event.cookies, event.url, result.data.token, result.data.expires_at);
    redirect(303, next);
  }
};
