# syntax=docker/dockerfile:1
FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:0.13.9 /uv /uvx /bin/

ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# Dependencies first, so code changes do not reinstall them.
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev --no-install-project

COPY alembic.ini ./
COPY migrations ./migrations
COPY app ./app

ENV PATH="/app/.venv/bin:$PATH" \
    DATABASE_URL=sqlite:////data/ficka.db \
    TEMP_DIR=/tmp/ficka

# The API runs as user "ficka" (uid/gid 1000). /data is created and owned by that
# user in the image, so a new named volume mounted there inherits the ownership.
RUN groupadd --system --gid 1000 ficka \
    && useradd --system --uid 1000 --gid 1000 --no-create-home --home-dir /nonexistent ficka \
    && mkdir -p /data /tmp/ficka \
    && chown 1000:1000 /data /tmp/ficka
USER ficka

EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]
