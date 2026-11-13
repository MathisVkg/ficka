import logging
from contextlib import asynccontextmanager
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.financial import router as financial_router
from app.api.v1.health import router
from app.core.config import get_settings
from app.core.errors import register_errors
from app.core.logging import configure_logging
from app.db.session import get_engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    logging.getLogger("ficka").info("API started")
    yield
    get_engine().dispose()


def create_app() -> FastAPI:
    app = FastAPI(title="Ficka API", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_settings().cors_origins,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Content-Type"],
    )

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        request.state.request_id = str(uuid4())
        started = perf_counter()
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        logging.getLogger("ficka").info(
            "request method=%s path=%s status=%s duration_ms=%.1f request_id=%s",
            request.method,
            request.url.path,
            response.status_code,
            (perf_counter() - started) * 1000,
            request.state.request_id,
        )
        return response

    register_errors(app)
    app.include_router(router, prefix="/api/v1")
    app.include_router(financial_router, prefix="/api/v1")
    return app


app = create_app()
