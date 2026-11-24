"""FastAPI application. All routers live under /api."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.exc import OperationalError
from sqlmodel import Session

from app import __version__
from app.api import api_router
from app.config import get_settings
from app.db import get_engine
from app.services import auth

settings = get_settings()
logging.basicConfig(level=settings.log_level.upper())
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    try:
        with Session(get_engine()) as session:
            purged = auth.purge_expired_sessions(session)
        if purged:
            logger.info("Purged %d expired sessions", purged)
    except OperationalError:
        logger.warning("Could not purge expired sessions (has the database been migrated?)")
    yield


app = FastAPI(
    title="Ficka API",
    version=__version__,
    lifespan=lifespan,
    # The interactive docs are public by nature, so they're off unless API_DOCS=true.
    docs_url="/api/docs" if settings.api_docs else None,
    redoc_url=None,
    openapi_url="/api/openapi.json" if settings.api_docs else None,
)
app.include_router(api_router)
