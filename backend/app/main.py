"""FastAPI application. All routers live under /api."""

import logging

from fastapi import FastAPI

from app import __version__
from app.api import api_router
from app.config import get_settings

logging.basicConfig(level=get_settings().log_level.upper())

app = FastAPI(
    title="Ficka API",
    version=__version__,
    docs_url="/api/docs",
    redoc_url=None,
    openapi_url="/api/openapi.json",
)
app.include_router(api_router)
