"""
Authentication dependencies for FastAPI.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import User

# HTTP Bearer token scheme
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """
    Get the current authenticated user from JWT token.
    Returns None if not authenticated (allows guest access).
    """
    if not credentials:
        return None
    
    # Decode the token
    payload = decode_token(credentials.credentials, expected_type="access")
    if not payload:
        return None
    
    user_id = payload.get("sub")
    if not user_id:
        return None
    
    # Get user from database
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user or not user.is_active:
        return None
    
    return user


async def get_current_user_required(
    current_user: Optional[User] = Depends(get_current_user)
) -> User:
    """
    Get the current authenticated user. Raises 401 if not authenticated.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return current_user


async def get_current_user_or_guest(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Get current user or guest information.
    Returns user info if authenticated, otherwise returns guest_id.
    """
    user = await get_current_user(credentials, db)
    
    if user:
        return {
            "type": "user",
            "user": user,
            "user_id": user.id,
            "guest_id": user.guest_id,
            "is_authenticated": True
        }
    
    # For guest access, we'll need to get guest_id from somewhere
    # This could be from a cookie, header, or query parameter
    return {
        "type": "guest", 
        "user": None,
        "user_id": None,
        "guest_id": None,  # Will be handled at endpoint level
        "is_authenticated": False
    }


async def verify_refresh_token(
    refresh_token: str,
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Verify refresh token and return associated user.
    """
    payload = decode_token(refresh_token, expected_type="refresh")
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    # Get user and verify refresh token matches
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user or not user.is_active or user.refresh_token != refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    return user