import { fail, redirect } from '@sveltejs/kit';
import { formString } from '#lib/forms.js';
import { api } from '#lib/server/api.js';
import { clearSessionCookie } from '#lib/server/session.js';
import type { Actions } from './$types';

const MIN_PASSWORD_LENGTH = 8;

export type PasswordErrors = Partial<Record<'current' | 'new' | 'confirm' | 'form', string>>;

function failPassword(status: number, errors: PasswordErrors) {
  return fail(status, { password: { errors, success: false } });
}

export const actions: Actions = {
  password: async (event) => {
    const form = await event.request.formData();
    const current = formString(form, 'current_password');
    const next = formString(form, 'new_password');
    const confirm = formString(form, 'confirm_password');

    const errors: PasswordErrors = {};
    if (!current) errors.current = 'Enter your current password.';
    if (next.length < MIN_PASSWORD_LENGTH) {
      errors.new = `Use at least ${MIN_PASSWORD_LENGTH} characters.`;
    }
    if (confirm !== next) errors.confirm = 'The passwords don’t match.';
    if (Object.keys(errors).length > 0) return failPassword(400, errors);

    const result = await api(event, '/api/auth/password', {
      method: 'POST',
      body: { current_password: current, new_password: next }
    });

    if (!result.ok) {
      if (result.status === 401) {
        clearSessionCookie(event.cookies, event.url);
        redirect(303, '/login?next=%2Fsettings%2Faccount');
      }
      if (result.code === 'validation_error') {
        const { current_password, new_password } = result.fields;
        if (current_password || new_password) {
          return failPassword(400, { current: current_password, new: new_password });
        }
      }
      return failPassword(result.status, { form: result.message });
    }

    return { password: { errors: {} as PasswordErrors, success: true } };
  }
};
