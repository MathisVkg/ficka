"""Authentication endpoints. Only `POST /api/auth/login` is public."""

import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

from app.api.deps import CurrentCompany, CurrentSession, CurrentUser, DbSession, protected_router
from app.errors import ValidationFailed
from app.models import AppUser
from app.services import auth

logger = logging.getLogger(__name__)

# Set by the SvelteKit server from `event.getClientAddress()`. Trusting a client-supplied
# header is safe here only because the API is never reachable from outside: it isn't
# published in Docker, and only the SvelteKit server calls it.
CLIENT_IP_HEADER = "X-Ficka-Client-IP"

INVALID_CREDENTIALS = "Incorrect email or password."
TOO_MANY_ATTEMPTS = "Too many attempts. Try again in a few minutes."

public_router = APIRouter(prefix="/auth", tags=["auth"])
router = protected_router(prefix="/auth", tags=["auth"])


class UserOut(BaseModel):
    id: int
    email: str
    display_name: str

    @classmethod
    def of(cls, user: AppUser) -> "UserOut":
        assert user.id is not None
        return cls(id=user.id, email=user.email, display_name=user.display_name)


class CompanyOut(BaseModel):
    id: int
    name: str


class LoginRequest(BaseModel):
    email: str = Field(min_length=1, max_length=320)
    password: str = Field(min_length=1, max_length=auth.MAX_PASSWORD_LENGTH)


class LoginResponse(BaseModel):
    token: str
    expires_at: datetime
    user: UserOut


class MeResponse(BaseModel):
    user: UserOut
    company: CompanyOut
    session_expires_at: datetime


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=auth.MAX_PASSWORD_LENGTH)
    new_password: str = Field(
        min_length=auth.MIN_PASSWORD_LENGTH, max_length=auth.MAX_PASSWORD_LENGTH
    )


def client_ip(request: Request) -> str:
    forwarded = request.headers.get(CLIENT_IP_HEADER, "").strip()
    if forwarded:
        return forwarded
    return request.client.host if request.client else "unknown"


@public_router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest, request: Request, session: DbSession) -> LoginResponse:
    ip = client_ip(request)
    limiter = auth.login_rate_limiter
    if limiter.is_blocked(body.email, ip):
        logger.warning("Login rate limit reached for a client at %s", ip)
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, detail=TOO_MANY_ATTEMPTS)

    user = auth.authenticate(session, body.email, body.password)
    if user is None:
        limiter.record_failure(body.email, ip)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail=INVALID_CREDENTIALS)

    limiter.reset(body.email, ip)
    token, auth_session = auth.create_session(session, user)
    logger.info("User %s logged in", user.id)
    return LoginResponse(token=token, expires_at=auth_session.expires_at, user=UserOut.of(user))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(session: DbSession, auth_session: CurrentSession) -> Response:
    auth.delete_session(session, auth_session)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=MeResponse)
def me(user: CurrentUser, company: CurrentCompany, auth_session: CurrentSession) -> MeResponse:
    assert company.id is not None
    return MeResponse(
        user=UserOut.of(user),
        company=CompanyOut(id=company.id, name=company.name),
        session_expires_at=auth_session.expires_at,
    )


@router.post("/password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    body: PasswordChangeRequest,
    session: DbSession,
    user: CurrentUser,
    auth_session: CurrentSession,
) -> Response:
    assert auth_session.id is not None
    try:
        auth.change_password(
            session,
            user,
            body.current_password,
            body.new_password,
            keep_session_id=auth_session.id,
        )
    except auth.WrongPasswordError as exc:
        message = "The current password is incorrect."
        raise ValidationFailed(message, fields={"current_password": message}) from exc
    logger.info("User %s changed their password", user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
