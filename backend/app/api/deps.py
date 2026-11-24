"""Shared dependencies for the routers: database session, current session, user, company.

Protected by default
--------------------
Every router except the two public endpoints (`GET /api/health`, `POST /api/auth/login`)
must be created with `protected_router()`, so all its routes require a valid session:

    from app.api.deps import CurrentCompany, protected_router

    router = protected_router(prefix="/entries", tags=["entries"])

    @router.get("")
    def list_entries(company: CurrentCompany): ...

The dependency is attached to the router itself, so a route can't forget it.
`tests/test_auth_routes.py` walks every registered route and fails if one other than
the public ones answers without a token.
"""

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session, select

from app.db import get_session
from app.models import AppUser, AuthSession, Company, UserCompany
from app.services import auth

logger = logging.getLogger(__name__)

_bearer = HTTPBearer(auto_error=False)

DbSession = Annotated[Session, Depends(get_session)]


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


def current_session(
    session: DbSession,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> AuthSession:
    """The live session for the bearer token; 401 if missing, unknown or expired."""
    if credentials is None or not credentials.credentials:
        raise _unauthorized()
    auth_session = auth.resolve_session(session, credentials.credentials)
    if auth_session is None:
        raise _unauthorized()
    return auth_session


CurrentSession = Annotated[AuthSession, Depends(current_session)]


def current_user(session: DbSession, auth_session: CurrentSession) -> AppUser:
    user = session.get(AppUser, auth_session.user_id)
    if user is None:  # cannot happen with ON DELETE CASCADE, but stay safe
        raise _unauthorized()
    return user


CurrentUser = Annotated[AppUser, Depends(current_user)]


def current_company(session: DbSession, user: CurrentUser) -> Company:
    """The user's single company (v1: one user, one company)."""
    company = session.exec(
        select(Company)
        .join(UserCompany, UserCompany.company_id == Company.id)  # type: ignore[arg-type]
        .where(UserCompany.user_id == user.id)
        .order_by(Company.id)  # type: ignore[arg-type]
    ).first()
    if company is None:
        logger.error(
            "User %s has no company in user_company; run `python -m app.cli init` again "
            "on a fresh database or repair the user_company link.",
            user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The account is not linked to a company",
        )
    return company


CurrentCompany = Annotated[Company, Depends(current_company)]


def protected_router(**kwargs: Any) -> APIRouter:
    """An APIRouter whose every route requires a valid session (see the module docstring)."""
    dependencies = [Depends(current_user), *kwargs.pop("dependencies", [])]
    return APIRouter(dependencies=dependencies, **kwargs)
