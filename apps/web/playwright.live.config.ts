import { defineConfig, devices } from "@playwright/test";
// Writes test entries: point only at a disposable, migrated test stack.
export default defineConfig({
  testDir: "./tests-live",
  workers: 1,
  retries: 0,
  use: {
    ...devices["Desktop Chrome"],
    baseURL: process.env.FICKA_E2E_BASE_URL ?? "http://localhost:3000",
    trace: "retain-on-failure",
  },
});
