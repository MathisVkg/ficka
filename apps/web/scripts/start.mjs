// Use the same standalone artifact layout as the production Docker image.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
const web = fileURLToPath(new URL("..", import.meta.url));
const server = path.join(web, ".next/standalone/apps/web");
fs.cpSync(path.join(web, ".next/static"), path.join(server, ".next/static"), {
  recursive: true,
});
process.env.HOSTNAME = process.env.HOSTNAME || "127.0.0.1";
await import(pathToFileURL(path.join(server, "server.js")).href);
