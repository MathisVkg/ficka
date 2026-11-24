import { redirect } from '@sveltejs/kit';
import { api } from '#lib/server/api.js';
import { clearSessionCookie } from '#lib/server/session.js';
import type { Actions, PageServerLoad } from './$types';

// Logging out is a POST form action only; a GET never logs anyone out.
export const load: PageServerLoad = () => {
  redirect(303, '/');
};

export const actions: Actions = {
  default: async (event) => {
    // Even if the API call fails, the browser forgets the session.
    await api(event, '/api/auth/logout', { method: 'POST' });
    clearSessionCookie(event.cookies, event.url);
    redirect(303, '/login');
  }
};
