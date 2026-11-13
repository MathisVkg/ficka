FROM python:3.13-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:0.13.8 /uv /usr/local/bin/uv
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
COPY apps/api/pyproject.toml apps/api/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

FROM python:3.13-slim
RUN useradd --create-home --uid 10001 ficka
WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY --chown=ficka:ficka apps/api/app ./app
COPY --chown=ficka:ficka apps/api/migrations ./migrations
COPY --chown=ficka:ficka apps/api/alembic.ini ./
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
USER ficka
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --no-access-log"]
