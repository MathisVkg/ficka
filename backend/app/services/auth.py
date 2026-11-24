"""Authentication: password verification, server-side sessions, login rate limiting.

Sessions
- The client gets a random token (`secrets.token_urlsafe(32)`, 32 random bytes).
- Only `sha256(token)` is stored, in `auth_session.id`; the raw token is never
  stored or logged.
- Lifetime is 30 days, sliding: a session used with less than 15 days left is
  extended to now + 30 days (at most about one write per 15 days per session).
- Expired sessions are deleted when they are looked up, and purged at startup.
"""

import hashlib
import secrets
import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from datetime import timedelta

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from sqlalchemy import delete
from sqlmodel import Session, col, select

from app.models import AppUser, AuthSession
from app.models.base import utc_now

SESSION_LIFETIME = timedelta(days=30)
SESSION_EXTEND_BELOW = timedelta(days=15)
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 1024  # bounds the hashing cost of a request

_hasher = PasswordHasher()  # argon2id with the library defaults
# Verified when the email is unknown, so the response time doesn't reveal which
# emails exist.
_DUMMY_HASH = _hasher.hash(secrets.token_urlsafe(16))


class PasswordTooShortError(ValueError):
    pass


class WrongPasswordError(ValueError):
    pass


def normalize_email(email: str) -> str:
    return email.strip().lower()


def hash_password(password: str) -> str:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise PasswordTooShortError(f"Passwords need at least {MIN_PASSWORD_LENGTH} characters")
    return _hasher.hash(password)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _verify(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def authenticate(session: Session, email: str, password: str) -> AppUser | None:
    """The user if the email and password match, otherwise None (always one argon2 verify)."""
    user = session.exec(select(AppUser).where(AppUser.email == normalize_email(email))).first()
    if user is None:
        _verify(_DUMMY_HASH, password)
        return None
    if not _verify(user.password_hash, password):
        return None
    if _hasher.check_needs_rehash(user.password_hash):
        user.password_hash = _hasher.hash(password)
    user.last_login_at = utc_now()
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def create_session(session: Session, user: AppUser) -> tuple[str, AuthSession]:
    """Create a session; returns the raw token (give it to the client) and the row."""
    assert user.id is not None
    token = secrets.token_urlsafe(32)
    now = utc_now()
    auth_session = AuthSession(
        id=hash_token(token), user_id=user.id, created_at=now, expires_at=now + SESSION_LIFETIME
    )
    session.add(auth_session)
    session.commit()
    session.refresh(auth_session)
    return token, auth_session


def resolve_session(session: Session, token: str) -> AuthSession | None:
    """The live session for this token, extending it if needed; None if unknown or expired."""
    auth_session = session.get(AuthSession, hash_token(token))
    if auth_session is None:
        return None
    now = utc_now()
    if auth_session.expires_at <= now:
        session.delete(auth_session)
        session.commit()
        return None
    if auth_session.expires_at - now < SESSION_EXTEND_BELOW:
        auth_session.expires_at = now + SESSION_LIFETIME
        session.add(auth_session)
        session.commit()
        session.refresh(auth_session)
    return auth_session


def delete_session(session: Session, auth_session: AuthSession) -> None:
    session.delete(auth_session)
    session.commit()


def delete_other_sessions(session: Session, user_id: int, keep_session_id: str) -> int:
    result = session.exec(
        delete(AuthSession).where(
            col(AuthSession.user_id) == user_id, col(AuthSession.id) != keep_session_id
        )
    )
    session.commit()
    return result.rowcount


def delete_all_sessions(session: Session, user_id: int) -> int:
    result = session.exec(delete(AuthSession).where(col(AuthSession.user_id) == user_id))
    session.commit()
    return result.rowcount


def set_password(session: Session, user: AppUser, new_password: str) -> None:
    """Replace the password hash (no check of the old password: CLI recovery)."""
    user.password_hash = hash_password(new_password)
    session.add(user)
    session.commit()


def change_password(
    session: Session,
    user: AppUser,
    current_password: str,
    new_password: str,
    keep_session_id: str,
) -> None:
    """Change the password and sign out every other session of the user."""
    if not _verify(user.password_hash, current_password):
        raise WrongPasswordError("The current password is incorrect")
    set_password(session, user, new_password)
    assert user.id is not None
    delete_other_sessions(session, user.id, keep_session_id)


def purge_expired_sessions(session: Session) -> int:
    result = session.exec(delete(AuthSession).where(col(AuthSession.expires_at) <= utc_now()))
    session.commit()
    return result.rowcount


@dataclass
class LoginRateLimiter:
    """At most `max_failures` failed logins per key within `window_seconds`.

    The key is (lower-cased email, client IP). State is kept in memory: that is
    enough for Ficka's single API process, but it is lost on restart and not
    shared between processes. Use a shared store if the API ever runs as several
    workers or replicas.
    """

    max_failures: int = 5
    window_seconds: float = 15 * 60
    clock: Callable[[], float] = time.monotonic

    def __post_init__(self) -> None:
        self._failures: dict[tuple[str, str], deque[float]] = {}
        self._lock = threading.Lock()

    def _recent(self, key: tuple[str, str]) -> deque[float]:
        attempts = self._failures.setdefault(key, deque())
        cutoff = self.clock() - self.window_seconds
        while attempts and attempts[0] <= cutoff:
            attempts.popleft()
        return attempts

    def is_blocked(self, email: str, ip: str) -> bool:
        key = (normalize_email(email), ip)
        with self._lock:
            blocked = len(self._recent(key)) >= self.max_failures
            if not self._failures.get(key):
                self._failures.pop(key, None)
            return blocked

    def record_failure(self, email: str, ip: str) -> None:
        with self._lock:
            self._recent((normalize_email(email), ip)).append(self.clock())

    def reset(self, email: str, ip: str) -> None:
        with self._lock:
            self._failures.pop((normalize_email(email), ip), None)


login_rate_limiter = LoginRateLimiter()
