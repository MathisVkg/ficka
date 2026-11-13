from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.schemas.health import ErrorResponse, HealthResponse
from app.services.health import check_database

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live", response_model=HealthResponse)
def live() -> HealthResponse:
    return HealthResponse(status="alive")


@router.get("/ready", response_model=HealthResponse, responses={503: {"model": ErrorResponse}})
def ready(session: Annotated[Session, Depends(get_session)]) -> HealthResponse:
    try:
        check_database(session)
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail="Database is unavailable") from None
    return HealthResponse(status="ready")
