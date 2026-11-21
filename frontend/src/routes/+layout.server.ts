import { API_URL } from '$app/env/private';
import type { LayoutServerLoad } from './$types';

interface Health {
  status: string;
  version: string;
  database: string;
}

export const load: LayoutServerLoad = async ({ fetch }) => {
  try {
    const response = await fetch(`${API_URL}/api/health`, { signal: AbortSignal.timeout(3000) });
    if (!response.ok) {
      return { api: { connected: false, version: null } };
    }
    const health = (await response.json()) as Health;
    return { api: { connected: health.status === 'ok', version: health.version } };
  } catch {
    return { api: { connected: false, version: null } };
  }
};
