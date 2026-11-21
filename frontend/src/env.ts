import { defineEnvVars } from '@sveltejs/kit/env';

/**
 * Environment variables, read when the server starts.
 * Private ones are only importable from server code, through `$app/env/private`.
 */
export const variables = defineEnvVars({
  API_URL: {
    description: 'Internal URL of the Ficka API, used server-side only (no trailing slash).',
    schema: (value) => (value?.trim() || 'http://localhost:8000').replace(/\/+$/, '')
  }
});
