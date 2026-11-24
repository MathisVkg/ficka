# Ficka

Ficka is a self-hosted web app that helps a small business (Belgium by default) visualize and estimate its finances: income, expenses, VAT and cash forecast.
It is not accounting software: every figure is an estimation, and it runs entirely on your own machine with no external services.

## Prerequisites

- [uv](https://docs.astral.sh/uv/) 0.13 or newer (it installs Python 3.13 for you)
- Node.js 24 LTS and npm 11
- Docker Desktop with Docker Compose v2 (only for the Docker setup)

## Development (PowerShell)

Backend, in a first terminal:

```powershell
cd backend
uv sync
uv run python -m app.cli init      # first time only: migrations, company, user, seed
uv run uvicorn app.main:app --reload --port 8000
```

Frontend, in a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173> and sign in with the account created by `init` (see [First login](#first-login)). The navigation shows "API connected" when the frontend reaches the backend.
The browser only ever talks to SvelteKit; SvelteKit calls the API server-side, through `API_URL`.

Useful commands:

```powershell
cd backend
uv run alembic upgrade head        # apply migrations
uv run python -m app.cli seed      # re-run the idempotent seed
uv run ruff check
uv run ruff format --check
```

```powershell
cd frontend
npm run check
npm run lint
npm run build
```

Configuration is read from environment variables (or `backend/.env`):

| Variable | Default | Meaning |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./data/ficka.db` | SQLite database |
| `TEMP_DIR` | system temp folder + `ficka` | where uploaded documents live while they are processed |
| `DOCUMENT_TTL_HOURS` | `24` | how long an abandoned upload is kept |
| `LOG_LEVEL` | `INFO` | log level |
| `API_DOCS` | `false` | serve the interactive API docs at `/api/docs` (development only: they need no login) |
| `API_URL` (frontend) | `http://localhost:8000` | internal URL SvelteKit uses to reach the API |

## Docker (local build)

`docker-compose.yml` builds the images from the source. No variables are needed; `FICKA_PORT` (default `3000`) and `ORIGIN` (default `http://localhost:3000`) can be set if needed.

```powershell
docker compose up -d --build
```

Then create the company and its owner, either interactively (the password is asked twice, hidden):

```powershell
docker compose exec api python -m app.cli init
```

or in one line with options (the password then stays in your shell history):

```powershell
docker compose exec api python -m app.cli init --company-name "My company" --email "me@example.com" --display-name "Me" --password "a-long-password"
```

Open <http://localhost:3000>. Only the web service is published; the API is reachable only inside the Compose network.
The SQLite database lives in the `ficka-data` volume, and temporary documents in a tmpfs mount.

The optional local LLM (Ollama) is started only with the `ai` profile:

```powershell
docker compose --profile ai up -d
```

## Deploy with Portainer (Repository method)

The server never builds anything. On every push to `main`, GitHub Actions builds the images and publishes them to the GitHub Container Registry as `ghcr.io/mathisvkg/ficka-api` and `ghcr.io/mathisvkg/ficka-web`. Portainer deploys [`deploy/portainer-compose.yml`](deploy/portainer-compose.yml), which only pulls those images.

1. **Publish the images.** Push to `main`, then open the repository's **Actions** tab on GitHub and check that the **images** workflow succeeded. It can also be started by hand there (**Run workflow**).
2. **First time only: make the images pullable.** On GitHub, open your profile → **Packages**, then for both `ficka-api` and `ficka-web`: **Package settings** → **Change visibility** → **Public** (simplest).
   If they should stay private, add the registry in Portainer instead: **Registries** → **Add registry** → **Custom registry**, URL `ghcr.io`, username = your GitHub user, password = a *classic* personal access token with only the `read:packages` scope.
3. **Create the stack.** Portainer → **Stacks** → **Add stack** → **Repository**:
   - Repository URL: this repository
   - Repository reference: `refs/heads/main`
   - Compose path: `deploy/portainer-compose.yml`
4. **Environment variables** (in the same screen, **Environment variables** → **Add an environment variable**):

   | Name | Required | Value |
   |---|---|---|
   | `ORIGIN` | yes | the URL you open in the browser, for example `http://<server-ip>:3000` (no trailing slash) |
   | `FICKA_PORT` | no | host port for the web app, default `3000` (keep it consistent with `ORIGIN`) |
   | `FICKA_TAG` | no | image tag, default `latest`; set `sha-xxxxxxx` (from the Actions run or the package page) to pin a version |

5. **Deploy, then initialize once.** Click **Deploy the stack**. When the `api` container is healthy, open it in Portainer (**Containers** → `api` → **Console**), keep the default user (or choose `ficka`, never `root`), connect with `/bin/sh`, and run:

   ```sh
   python -m app.cli init
   ```

   It asks for the company name, your email, display name and password. The one-line form with options shown in the Docker section also works there.
   Then open the `ORIGIN` URL in your browser.
6. **Update.** Push to `main` and wait for the **images** workflow to finish. In Portainer, open the stack and click **Pull and redeploy**, with **Re-pull image** enabled. The `ficka-data` volume keeps the data across redeploys.
7. **Troubleshooting.**
   - *Forms are rejected* (`Cross-site POST form submissions are forbidden`): `ORIGIN` doesn't exactly match the URL in the browser (scheme, host and port).
   - *Image pull denied / not found*: the package is private and Portainer has no `ghcr.io` registry credential (step 2), or the workflow hasn't published that tag yet.
   - *`init` says "Running as root"*: the console was opened as `root`; reconnect with the default user.
   - *The web app says "API unavailable"*: check the `api` container logs in Portainer.

## First login

Ficka has a single account, created by `python -m app.cli init` (there's no registration page).

1. Open Ficka in the browser: <http://localhost:5173> in development, <http://localhost:3000> with the local Docker setup, or your `ORIGIN` URL on the server. Every page redirects to the sign-in page until you're logged in.
2. Sign in with the email and password you gave to `init`. You stay signed in for 30 days; each visit in the second half of that period extends it again.
3. **Log out** is at the bottom of the navigation. To change your password, open **Settings** → **Account**. Changing it signs out your other sessions (other browsers and devices).

After 5 wrong passwords for the same email from the same address, sign-in is blocked for 15 minutes ("Too many attempts").

## Forgot password

There's no email reset: the password is reset from the command line, in the `api` container. This also signs out every session of that account.

- **Portainer:** **Containers** → `api` → **Console**, keep the default user (never `root`), connect with `/bin/sh`, then run:

  ```sh
  python -m app.cli reset-password
  ```

  It asks for the email and the new password (hidden, twice).

- **Local Docker:**

  ```powershell
  docker compose exec api python -m app.cli reset-password
  ```

- **Development:**

  ```powershell
  cd backend
  uv run python -m app.cli reset-password
  ```

For scripting, `--email` can be given as an option (the password is still asked unless the hidden `--password` option is used, which leaves it in your shell history).

## Project structure

```
ficka/
├── backend/              FastAPI API (Python, uv)
│   ├── app/
│   │   ├── main.py       FastAPI app, routers under /api
│   │   ├── config.py     settings (pydantic-settings)
│   │   ├── db.py         engine and sessions (SQLite pragmas)
│   │   ├── models/       SQLModel tables, one file per area
│   │   ├── services/     business logic (one package per area)
│   │   ├── api/          HTTP routers
│   │   ├── cli.py        command line: init, seed
│   │   └── seed.py       idempotent seed data
│   ├── migrations/       Alembic migrations
│   └── Dockerfile
├── frontend/             SvelteKit app (TypeScript, Tailwind CSS v4, bits-ui)
│   ├── src/
│   └── Dockerfile
├── deploy/
│   └── portainer-compose.yml   server stack: pulls prebuilt images from GHCR
├── .github/workflows/
│   └── images.yml        builds and publishes the images on every push to main
├── docs/                 decisions, data model, reference schema
└── docker-compose.yml    local stack: builds the images from source
```
