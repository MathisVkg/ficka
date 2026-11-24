"""HTTP routers, all mounted under /api.

Public: `GET /api/health` and `POST /api/auth/login`. Every other router must be
built with `app.api.deps.protected_router()`.
"""

from fastapi import APIRouter

from app.api import auth, counterparties, entries, health, reference

api_router = APIRouter(prefix="/api")
api_router.include_router(health.router)
api_router.include_router(auth.public_router)
api_router.include_router(auth.router)
api_router.include_router(reference.router)
api_router.include_router(counterparties.router)
api_router.include_router(entries.router)
