"""Main API router that combines all route modules."""

from fastapi import APIRouter

from app.api.profile import router as profile_router

# Create main API router
api_router = APIRouter(prefix="/api/v1")

# Include all route modules
api_router.include_router(profile_router)

# Health check endpoint
@api_router.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "reGen API"}