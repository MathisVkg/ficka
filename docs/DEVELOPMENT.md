# Local development

Run commands from the repository root unless a step changes directory. Keep the existing `.env` if already configured; never commit it.

## Windows prerequisites

Install Node.js **24** from [Node.js downloads](https://nodejs.org/en/download). Then in PowerShell:

```powershell
npm install --global pnpm@11.25.0
winget install --id astral-sh.uv --exact
winget install --id Docker.DockerDesktop --exact
```

Open a new terminal so PATH updates take effect. Start Docker Desktop and use Linux containers with its WSL 2 backend. If winget is unavailable, use the [uv installation guide](https://docs.astral.sh/uv/getting-started/installation/) and [Docker Windows installation guide](https://docs.docker.com/desktop/setup/install/windows-install/). uv installs Python 3.13; a separate global Python install is unnecessary.

```powershell
node --version
pnpm --version
uv --version
docker version
docker compose version
```

Docker version must show a working server, not just a client. For an explicitly configured external PostgreSQL instance, skip Docker entirely.

## 1. Prepare the shared environment

```powershell
Set-Location C:\Users\zeyros\Documents\repository\ficka
Copy-Item .env.example .env
notepad .env
pnpm install --frozen-lockfile
uv python install 3.13
uv sync --project apps/api --frozen
```

Set a real `POSTGRES_PASSWORD`. The user, password and database name are shared by native API and container initialization. Passwords may contain URL-special characters when using separate variables; quote values with special dotenv characters using single quotes. For widest compatibility with shell/Portainer interpolation, a long random alphanumeric password is straightforward.

| Setting                     | Native development                                 | Local/Portainer containers                            |
| --------------------------- | -------------------------------------------------- | ----------------------------------------------------- |
| `POSTGRES_HOST`             | `127.0.0.1`, or your external DB hostname          | Fixed to `db` by Compose                              |
| `POSTGRES_PORT`             | Host database port, also used by native DB overlay | Fixed to `5432` internally                            |
| `POSTGRES_USER/PASSWORD/DB` | Root `.env`                                        | Forwarded explicitly by Compose                       |
| `DATABASE_URL`              | Optional override for an external instance         | Not forwarded; separate fields are used               |
| `API_INTERNAL_URL`          | `http://127.0.0.1:8000`                            | Fixed to `http://api:8000`                            |
| `CORS_ORIGINS`              | `[]` for same-origin web adapter                   | `[]` unless direct API access is deliberately enabled |
| `WEB_PORT`                  | Compose port only; native Next.js defaults to 3000 | Published host port, default 3000                     |

uv loads the root file through `--env-file ../../.env`. Root `pnpm dev` loads the same file on the Next.js server. Existing process environment variables take precedence. Avoid a second conflicting `apps/web/.env.local` or `apps/api/.env`. Root `.env` is not baked into images or exposed to the browser.

If you reuse a Task 01 `.env`, comment out its old `DATABASE_URL` to use the new shared PostgreSQL fields. Retain a URL only when you deliberately want it to override those fields.

For an external PostgreSQL database, either set the separate fields to its host/port/user/password/database, or uncomment `DATABASE_URL` using `postgresql+psycopg://`. A URL takes precedence and its password must be percent-encoded. Add `?sslmode=require` when required by your database provider. Ensure the database exists and the account may run migrations.

## 2. Start PostgreSQL (skip for an external database)

```powershell
pnpm dev:db
# Equivalent underlying command:
docker compose -f compose.yaml -f compose.dev.yaml up -d --wait db
docker compose -f compose.yaml -f compose.dev.yaml ps db
```

Only PostgreSQL starts. Its host port binds to 127.0.0.1, preventing LAN exposure. The tracked overlay removes the need to write a private Compose override. If 5432 is occupied, choose another `POSTGRES_PORT` in root `.env` and use the same value for native API access.

## 3. Migrate and start the API

In terminal one:

```powershell
Set-Location apps/api
uv run --env-file ../../.env alembic upgrade head
uv run --env-file ../../.env uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Leave it running. [API docs](http://127.0.0.1:8000/docs) are available directly. In another terminal:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/health/live
Invoke-RestMethod http://127.0.0.1:8000/api/v1/health/ready
```

Liveness returns alive without a database query; readiness returns ready only after querying PostgreSQL.

## 4. Start the frontend

In terminal two, at repository root:

```powershell
pnpm dev
Start-Process http://localhost:3000
```

The dashboard should show **All systems connected**. Test the full server-side connection with `Invoke-RestMethod http://localhost:3000/api/health/ready`. Restart `pnpm dev` after changing its root environment values.

For a different native web port set `$env:PORT = "3001"` before `pnpm dev`. The backend URL remains a server setting, never a `NEXT_PUBLIC_` variable. The browser uses its current origin even when web is opened through a LAN address.

## Stop and switch modes

Press Ctrl+C in both native terminals, then run `pnpm dev:db:stop` (underlying command: `docker compose -f compose.yaml -f compose.dev.yaml stop db`). Stop external databases using their own management tools.

For the full local Docker stack:

```powershell
docker compose -f compose.yaml up --build --wait
docker compose -f compose.yaml logs -f --tail=100
docker compose -f compose.yaml down
```

This mode builds both applications and publishes web only on localhost. Do not run native and full-container modes simultaneously on the same ports. They intentionally share the same project name and named database volume; keep credentials consistent.

## Checks and migrations

```powershell
pnpm lint
pnpm typecheck
pnpm format:check
pnpm build
pnpm --filter @ficka/web exec playwright install chromium
pnpm test
Set-Location apps/api
uv run ruff check .
uv run ruff format --check .
uv run pytest
# With a running disposable database, after migration:
$env:RUN_DB_TESTS = "1"
uv run --env-file ../../.env pytest tests/integration
Remove-Item Env:RUN_DB_TESTS
```

Next.js may generate or update `apps/web/AGENTS.md` during the first development start. Its framework guidance is tracked so future starts do not leave a new untracked file. The generated `next-env.d.ts` temporarily points at development types during `next dev`; a production build restores its production references.

Browser tests build and start the standalone production artifact. Stop the development frontend first so tests exercise the production build. The integration test is skipped by default; unit tests require no live database.

From `apps/api`, create future migrations with `uv run --env-file ../../.env alembic revision --autogenerate -m description`, review the generated SQL, and run `uv run --env-file ../../.env alembic upgrade head`. Test downgrade on a disposable database. Format with `pnpm format` and `uv run ruff format .`. Keep both dependency lockfiles committed.

## Troubleshooting

- **docker not found / cannot connect:** install/start Docker Desktop, reopen PowerShell and confirm Linux containers and WSL 2 are running. A downloaded CLI alone cannot run containers.
- **Database unavailable:** inspect `docker compose -f compose.yaml logs --tail=100 db`, check the host port and migration command. Native code must use a host address; the service name `db` only resolves inside Docker.
- **Authentication fails after editing .env:** PostgreSQL initialization variables only apply to a new volume. Rotate the existing role password explicitly and update configuration; changing the file does not rotate the database password.
- **Web banner but API ready:** verify the root `API_INTERNAL_URL`, restart web, then request `/api/health/ready` through web. Do not put `api:8000` into a browser URL or add wildcard CORS.
- **Port already used:** stop the other mode, or adjust host ports and the native API URL consistently.
- **Windows build EBUSY:** stop the production preview before rebuilding `.next/standalone`.

Keep the database volume. Never use `down -v` to fix a password problem on a database you need. Deployment, backup and registry guidance is in [DEPLOYMENT.md](DEPLOYMENT.md).
