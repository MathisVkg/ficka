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

Open <http://localhost:5173>. The navigation shows "API connected" when the frontend reaches the backend.

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
| `API_URL` (frontend) | `http://localhost:8000` | internal URL SvelteKit uses to reach the API |

## Docker

```powershell
docker compose up -d --build
docker compose exec api python -m app.cli init
```

Open <http://localhost:3000>. Only the web service is published; the API is reachable only inside the Compose network.
The SQLite database lives in the `ficka-data` volume, and temporary documents in a tmpfs mount.

The optional local LLM (Ollama) is started only with the `ai` profile:

```powershell
docker compose --profile ai up -d
```

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
├── docs/                 decisions, data model, reference schema
└── docker-compose.yml
```
