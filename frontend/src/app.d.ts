// See https://svelte.dev/docs/kit/types#app.d.ts
// for information about these interfaces
import type { SessionCompany, SessionUser } from '#lib/server/session.js';

declare global {
  namespace App {
    // interface Error {}
    interface Locals {
      /** The logged-in user, or null (set by hooks.server.ts on every request). */
      user: SessionUser | null;
      /** The user's company (v1: exactly one), or null when not logged in. */
      company: SessionCompany | null;
    }
    // interface PageData {}
    // interface PageState {}
    // interface Platform {}
  }
}

export {};
