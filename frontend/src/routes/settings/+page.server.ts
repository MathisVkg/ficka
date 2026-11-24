import { error, fail, redirect } from '@sveltejs/kit';
import { todayIso } from '#lib/dates.js';
import { formString } from '#lib/forms.js';
import { api } from '#lib/server/api.js';
import { clearSessionCookie } from '#lib/server/session.js';
import type { Category, Direction, VatRate } from '#lib/types.js';
import type { Actions, PageServerLoad } from './$types';

export const load: PageServerLoad = async (event) => {
  const [categories, rates] = await Promise.all([
    api<Category[]>(event, '/api/categories'),
    api<VatRate[]>(event, '/api/vat-rates', { query: { on: todayIso() } })
  ]);
  if (!categories.ok) error(categories.unreachable ? 503 : categories.status, categories.message);
  return { categories: categories.data, rates: rates.ok ? rates.data : [] };
};

export interface CategoryResult {
  action: 'create' | 'update' | 'move' | 'delete';
  id?: number;
  direction?: Direction;
  errors: Record<string, string>;
  message?: string | null;
  values?: { name: string; default_vat_rate_bp: string };
}

function failCategory(status: number, result: CategoryResult) {
  return fail(status, { category: result });
}

function direction(form: FormData): Direction {
  return formString(form, 'direction') === 'income' ? 'income' : 'expense';
}

function rateOf(value: string): number | null {
  return /^\d+$/.test(value) ? Number(value) : null;
}

function idOf(form: FormData, name = 'id'): number | null {
  const value = formString(form, name);
  return /^\d+$/.test(value) ? Number(value) : null;
}

const MIN_PASSWORD_LENGTH = 8;

export type PasswordErrors = Partial<Record<'current' | 'new' | 'confirm' | 'form', string>>;

function failPassword(status: number, errors: PasswordErrors) {
  return fail(status, { password: { errors, success: false } });
}

export const actions: Actions = {
  createCategory: async (event) => {
    const form = await event.request.formData();
    const values = {
      name: formString(form, 'name'),
      default_vat_rate_bp: formString(form, 'default_vat_rate_bp')
    };
    const dir = direction(form);
    const result = await api(event, '/api/categories', {
      method: 'POST',
      body: {
        direction: dir,
        name: values.name,
        default_vat_rate_bp: rateOf(values.default_vat_rate_bp)
      }
    });
    if (!result.ok) {
      return failCategory(result.status, {
        action: 'create',
        direction: dir,
        errors: result.fields,
        message: Object.keys(result.fields).length ? null : result.message,
        values
      });
    }
    return { category: { action: 'create', direction: dir, errors: {} } satisfies CategoryResult };
  },

  updateCategory: async (event) => {
    const form = await event.request.formData();
    const id = idOf(form);
    const values = {
      name: formString(form, 'name'),
      default_vat_rate_bp: formString(form, 'default_vat_rate_bp')
    };
    if (id === null)
      return failCategory(400, { action: 'update', errors: {}, message: 'Unknown category.' });
    const result = await api(event, `/api/categories/${id}`, {
      method: 'PATCH',
      body: { name: values.name, default_vat_rate_bp: rateOf(values.default_vat_rate_bp) }
    });
    if (!result.ok) {
      return failCategory(result.status, {
        action: 'update',
        id,
        errors: result.fields,
        message: Object.keys(result.fields).length ? null : result.message,
        values
      });
    }
    return { category: { action: 'update', id, errors: {} } satisfies CategoryResult };
  },

  moveCategory: async (event) => {
    const form = await event.request.formData();
    const id = idOf(form);
    const dir = direction(form);
    const step = formString(form, 'step') === 'up' ? -1 : 1;
    const list = await api<Category[]>(event, '/api/categories', { query: { direction: dir } });
    if (!list.ok || id === null) {
      return failCategory(400, {
        action: 'move',
        errors: {},
        message: 'The order couldn’t be changed.'
      });
    }
    const ids = list.data.map((c) => c.id);
    const index = ids.indexOf(id);
    const target = index + step;
    if (index < 0 || target < 0 || target >= ids.length) {
      return { category: { action: 'move', id, errors: {} } satisfies CategoryResult };
    }
    [ids[index], ids[target]] = [ids[target], ids[index]];
    const result = await api(event, '/api/categories/reorder', {
      method: 'POST',
      body: { direction: dir, ids }
    });
    if (!result.ok)
      return failCategory(result.status, {
        action: 'move',
        id,
        errors: {},
        message: result.message
      });
    return { category: { action: 'move', id, errors: {} } satisfies CategoryResult };
  },

  deleteCategory: async (event) => {
    const form = await event.request.formData();
    const id = idOf(form);
    const reassignTo = idOf(form, 'reassign_to');
    if (id === null)
      return failCategory(400, { action: 'delete', errors: {}, message: 'Unknown category.' });
    const result = await api(event, `/api/categories/${id}`, {
      method: 'DELETE',
      query: { reassign_to: reassignTo }
    });
    if (!result.ok) {
      return failCategory(result.status, {
        action: 'delete',
        id,
        errors: result.fields,
        message: result.message
      });
    }
    return { category: { action: 'delete', id, errors: {} } satisfies CategoryResult };
  },

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
        redirect(303, '/login?next=%2Fsettings');
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
