// Next.js loads app-local env files; load the shared root .env for native dev.
import { existsSync } from "node:fs";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";
const envFile = fileURLToPath(new URL("../.env", import.meta.url));
if (existsSync(envFile)) process.loadEnvFile(envFile);
const web = fileURLToPath(new URL("../apps/web/", import.meta.url));
const require = createRequire(
  new URL("../apps/web/package.json", import.meta.url),
);
const next = require.resolve("next/dist/bin/next");
const child = spawn(process.execPath, [next, "dev", "--hostname", "0.0.0.0"], {
  cwd: web,
  env: process.env,
  stdio: "inherit",
  windowsHide: true,
});
child.on("error", (error) => {
  console.error(error.message);
  process.exitCode = 1;
});
child.on("exit", (code) => {
  process.exitCode = code ?? 1;
});
