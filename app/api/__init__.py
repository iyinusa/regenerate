"""API routes for reGen application."""

from app.api.routes import api_router
from app.api.profile import router as profile_router
from app.api.auth import router as auth_router

__all__ = [
    "api_router",
    "profile_router",
    "auth_router",
]