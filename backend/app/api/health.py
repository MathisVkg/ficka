"""Health check: is the API up, and can it reach the database?"""

import logging

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlmodel import Session

from app import __version__
from app.db import get_session

logger = logging.getLogger(__name__)

router = APIRouter(tags=["system"])


@router.get("/health")
def health(response: Response, session: Session = Depends(get_session)) -> dict[str, str]:
    try:
        session.connection().execute(text("SELECT 1"))
        database = "ok"
    except Exception:
        logger.exception("Database health check failed")
        database = "error"

    if database != "ok":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "error", "version": __version__, "database": database}
    return {"status": "ok", "version": __version__, "database": database}
