import { api } from '#lib/server/api.js';
import type { LayoutServerLoad } from './$types';

interface Health {
  status: string;
  version: string;
  database: string;
}

export const load: LayoutServerLoad = async (event) => {
  const health = await api<Health>(event, '/api/health', { token: null, timeoutMs: 3000 });
  return {
    user: event.locals.user,
    company: event.locals.company,
    api: {
      connected: health.ok && health.data.status === 'ok',
      version: health.ok ? health.data.version : null
    }
  };
};
