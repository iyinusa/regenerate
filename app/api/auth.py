"""OAuth Authentication Routes for GitHub and LinkedIn.

This module handles OAuth 2.0 authentication flows for both GitHub and LinkedIn,
enabling enhanced profile data extraction and enrichment.
"""

import logging
import secrets
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, HTTPException, status, Depends, Query, Request
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.core.config import settings
from app.db.session import get_db
from app.models.user import User

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/auth", tags=["authentication"])

# In-memory state storage (use Redis in production)
_oauth_states: Dict[str, Dict[str, Any]] = {}


def generate_oauth_state(guest_id: str, provider: str) -> str:
    """Generate a secure OAuth state parameter.
    
    Args:
        guest_id: Guest user identifier
        provider: OAuth provider name
        
    Returns:
        Unique state string
    """
    state = secrets.token_urlsafe(32)
    _oauth_states[state] = {
        "guest_id": guest_id,
        "provider": provider,
        "created_at": datetime.utcnow(),
    }
    return state


def verify_oauth_state(state: str) -> Optional[Dict[str, Any]]:
    """Verify and consume an OAuth state.
    
    Args:
        state: State string to verify
        
    Returns:
        State data if valid, None otherwise
    """
    state_data = _oauth_states.pop(state, None)
    
    if not state_data:
        return None
    
    # Check if state is expired (5 minutes)
    if datetime.utcnow() - state_data["created_at"] > timedelta(minutes=5):
        return None
    
    return state_data


# =============================================================================
# GitHub OAuth
# =============================================================================

@router.get(
    "/github",
    summary="Initiate GitHub OAuth",
    description="Start the GitHub OAuth flow for repository access and profile enrichment."
)
async def github_oauth_start(
    guest_id: str = Query(..., description="Guest user ID for linking OAuth"),
):
    """Start GitHub OAuth flow.
    
    Args:
        guest_id: Guest user ID to link OAuth credentials
        
    Returns:
        Redirect URL for GitHub OAuth
    """
    if not settings.github_client_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GitHub OAuth is not configured"
        )
    
    state = generate_oauth_state(guest_id, "github")
    
    # GitHub OAuth scopes for profile and repo access
    scopes = "read:user user:email repo read:org"
    
    params = {
        "client_id": settings.github_client_id,
        "redirect_uri": settings.github_redirect_uri,
        "scope": scopes,
        "state": state,
        "allow_signup": "false"
    }
    
    auth_url = f"https://github.com/login/oauth/authorize?{urlencode(params)}"
    
    return {"redirect_url": auth_url}


@router.get(
    "/github/callback",
    summary="GitHub OAuth Callback",
    description="Handle GitHub OAuth callback and store credentials."
)
async def github_oauth_callback(
    code: str = Query(..., description="Authorization code from GitHub"),
    state: str = Query(..., description="OAuth state parameter"),
    db: AsyncSession = Depends(get_db)
):
    """Handle GitHub OAuth callback.
    
    Args:
        code: Authorization code from GitHub
        state: OAuth state for verification
        db: Database session
        
    Returns:
        Redirect to frontend with success/error
    """
    # Verify state
    state_data = verify_oauth_state(state)
    if not state_data:
        logger.warning("Invalid or expired OAuth state")
        return RedirectResponse(
            url=f"{settings.base_url}/?error=invalid_state",
            status_code=status.HTTP_302_FOUND
        )
    
    guest_id = state_data["guest_id"]
    
    try:
        # Exchange code for access token
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                "https://github.com/login/oauth/access_token",
                data={
                    "client_id": settings.github_client_id,
                    "client_secret": settings.github_client_secret,
                    "code": code,
                    "redirect_uri": settings.github_redirect_uri,
                },
                headers={"Accept": "application/json"}
            )
            
            if token_response.status_code != 200:
                logger.error(f"GitHub token exchange failed: {token_response.text}")
                return RedirectResponse(
                    url=f"{settings.base_url}/?error=token_exchange_failed",
                    status_code=status.HTTP_302_FOUND
                )
            
            token_data = token_response.json()
            
            if "error" in token_data:
                logger.error(f"GitHub OAuth error: {token_data}")
                return RedirectResponse(
                    url=f"{settings.base_url}/?error={token_data.get('error')}",
                    status_code=status.HTTP_302_FOUND
                )
            
            access_token = token_data.get("access_token")
            scopes = token_data.get("scope", "")
            
            # Fetch GitHub user info
            user_response = await client.get(
                "https://api.github.com/user",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github+json"
                }
            )
            
            if user_response.status_code != 200:
                logger.error(f"Failed to fetch GitHub user: {user_response.text}")
                return RedirectResponse(
                    url=f"{settings.base_url}/?error=user_fetch_failed",
                    status_code=status.HTTP_302_FOUND
                )
            
            github_user = user_response.json()
            github_id = str(github_user.get("id"))
            github_username = github_user.get("login")
            
            # Update user record with GitHub OAuth credentials
            result = await db.execute(
                select(User).where(User.guest_id == guest_id)
            )
            user = result.scalar_one_or_none()
            
            if user:
                await db.execute(
                    update(User)
                    .where(User.id == user.id)
                    .values(
                        github_id=github_id,
                        github_username=github_username,
                        github_access_token=access_token,
                        github_scopes=scopes,
                        github_token_expires_at=None,  # GitHub tokens don't expire unless revoked
                        full_name=user.full_name or github_user.get("name"),
                        email=user.email or github_user.get("email"),
                    )
                )
                await db.commit()
                logger.info(f"Updated user {user.id} with GitHub OAuth credentials")
            else:
                logger.warning(f"User not found for guest_id: {guest_id}")
            
            # Redirect to frontend with success
            return RedirectResponse(
                url=f"{settings.base_url}/?github_connected=true&username={github_username}",
                status_code=status.HTTP_302_FOUND
            )
            
    except Exception as e:
        logger.error(f"GitHub OAuth callback error: {e}")
        return RedirectResponse(
            url=f"{settings.base_url}/?error=oauth_failed",
            status_code=status.HTTP_302_FOUND
        )


@router.get(
    "/github/status",
    summary="Check GitHub OAuth Status",
    description="Check if a user has connected their GitHub account."
)
async def github_oauth_status(
    guest_id: str = Query(..., description="Guest user ID"),
    db: AsyncSession = Depends(get_db)
):
    """Check GitHub OAuth connection status.
    
    Args:
        guest_id: Guest user ID
        db: Database session
        
    Returns:
        GitHub connection status
    """
    result = await db.execute(
        select(User).where(User.guest_id == guest_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        return {"connected": False, "message": "User not found"}
    
    if user.github_access_token:
        return {
            "connected": True,
            "username": user.github_username,
            "scopes": user.github_scopes,
        }
    
    return {"connected": False}


# =============================================================================
# LinkedIn OAuth
# =============================================================================

@router.get(
    "/linkedin",
    summary="Initiate LinkedIn OAuth",
    description="Start the LinkedIn OAuth flow for profile access."
)
async def linkedin_oauth_start(
    guest_id: str = Query(..., description="Guest user ID for linking OAuth"),
):
    """Start LinkedIn OAuth flow.
    
    Args:
        guest_id: Guest user ID to link OAuth credentials
        
    Returns:
        Redirect URL for LinkedIn OAuth
    """
    if not settings.linkedin_client_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LinkedIn OAuth is not configured"
        )
    
    state = generate_oauth_state(guest_id, "linkedin")
    
    # LinkedIn OAuth scopes
    scopes = "openid profile email"
    
    params = {
        "response_type": "code",
        "client_id": settings.linkedin_client_id,
        "redirect_uri": settings.linkedin_redirect_uri,
        "state": state,
        "scope": scopes,
    }
    
    auth_url = f"https://www.linkedin.com/oauth/v2/authorization?{urlencode(params)}"
    
    return {"redirect_url": auth_url}


@router.get(
    "/linkedin/callback",
    summary="LinkedIn OAuth Callback",
    description="Handle LinkedIn OAuth callback and store credentials."
)
async def linkedin_oauth_callback(
    code: str = Query(..., description="Authorization code from LinkedIn"),
    state: str = Query(..., description="OAuth state parameter"),
    db: AsyncSession = Depends(get_db)
):
    """Handle LinkedIn OAuth callback.
    
    Args:
        code: Authorization code from LinkedIn
        state: OAuth state for verification
        db: Database session
        
    Returns:
        Redirect to frontend with success/error
    """
    # Verify state
    state_data = verify_oauth_state(state)
    if not state_data:
        logger.warning("Invalid or expired OAuth state")
        return RedirectResponse(
            url=f"{settings.base_url}/?error=invalid_state",
            status_code=status.HTTP_302_FOUND
        )
    
    guest_id = state_data["guest_id"]
    
    try:
        # Exchange code for access token
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                "https://www.linkedin.com/oauth/v2/accessToken",
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "client_id": settings.linkedin_client_id,
                    "client_secret": settings.linkedin_client_secret,
                    "redirect_uri": settings.linkedin_redirect_uri,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if token_response.status_code != 200:
                logger.error(f"LinkedIn token exchange failed: {token_response.text}")
                return RedirectResponse(
                    url=f"{settings.base_url}/?error=token_exchange_failed",
                    status_code=status.HTTP_302_FOUND
                )
            
            token_data = token_response.json()
            
            if "error" in token_data:
                logger.error(f"LinkedIn OAuth error: {token_data}")
                return RedirectResponse(
                    url=f"{settings.base_url}/?error={token_data.get('error')}",
                    status_code=status.HTTP_302_FOUND
                )
            
            access_token = token_data.get("access_token")
            expires_in = token_data.get("expires_in", 5184000)  # Default 60 days
            token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
            
            # Fetch LinkedIn user info using OpenID
            userinfo_response = await client.get(
                "https://api.linkedin.com/v2/userinfo",
                headers={
                    "Authorization": f"Bearer {access_token}",
                }
            )
            
            if userinfo_response.status_code != 200:
                logger.error(f"Failed to fetch LinkedIn user: {userinfo_response.text}")
                return RedirectResponse(
                    url=f"{settings.base_url}/?error=user_fetch_failed",
                    status_code=status.HTTP_302_FOUND
                )
            
            linkedin_user = userinfo_response.json()
            linkedin_id = linkedin_user.get("sub")
            full_name = linkedin_user.get("name")
            email = linkedin_user.get("email")
            
            # Update user record with LinkedIn OAuth credentials
            result = await db.execute(
                select(User).where(User.guest_id == guest_id)
            )
            user = result.scalar_one_or_none()
            
            if user:
                await db.execute(
                    update(User)
                    .where(User.id == user.id)
                    .values(
                        linkedin_id=linkedin_id,
                        linkedin_access_token=access_token,
                        linkedin_token_expires_at=token_expires_at,
                        full_name=user.full_name or full_name,
                        email=user.email or email,
                    )
                )
                await db.commit()
                logger.info(f"Updated user {user.id} with LinkedIn OAuth credentials")
            else:
                logger.warning(f"User not found for guest_id: {guest_id}")
            
            # Redirect to frontend with success
            return RedirectResponse(
                url=f"{settings.base_url}/?linkedin_connected=true",
                status_code=status.HTTP_302_FOUND
            )
            
    except Exception as e:
        logger.error(f"LinkedIn OAuth callback error: {e}")
        return RedirectResponse(
            url=f"{settings.base_url}/?error=oauth_failed",
            status_code=status.HTTP_302_FOUND
        )


@router.get(
    "/linkedin/status",
    summary="Check LinkedIn OAuth Status",
    description="Check if a user has connected their LinkedIn account."
)
async def linkedin_oauth_status(
    guest_id: str = Query(..., description="Guest user ID"),
    db: AsyncSession = Depends(get_db)
):
    """Check LinkedIn OAuth connection status.
    
    Args:
        guest_id: Guest user ID
        db: Database session
        
    Returns:
        LinkedIn connection status
    """
    result = await db.execute(
        select(User).where(User.guest_id == guest_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        return {"connected": False, "message": "User not found"}
    
    if user.linkedin_access_token:
        # Check if token is expired
        is_expired = (
            user.linkedin_token_expires_at and 
            user.linkedin_token_expires_at < datetime.utcnow()
        )
        return {
            "connected": True,
            "expired": is_expired,
            "profile_url": user.linkedin_profile_url,
        }
    
    return {"connected": False}


@router.get(
    "/status",
    summary="Get All OAuth Status",
    description="Get the OAuth connection status for all providers."
)
async def get_all_oauth_status(
    guest_id: str = Query(..., description="Guest user ID"),
    db: AsyncSession = Depends(get_db)
):
    """Get OAuth status for all providers.
    
    Args:
        guest_id: Guest user ID
        db: Database session
        
    Returns:
        OAuth status for GitHub and LinkedIn
    """
    result = await db.execute(
        select(User).where(User.guest_id == guest_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        return {
            "github": {"connected": False},
            "linkedin": {"connected": False},
            "user_found": False
        }
    
    github_status = {
        "connected": bool(user.github_access_token),
        "username": user.github_username,
    }
    
    linkedin_status = {
        "connected": bool(user.linkedin_access_token),
        "expired": (
            user.linkedin_token_expires_at and 
            user.linkedin_token_expires_at < datetime.utcnow()
        ) if user.linkedin_access_token else None,
    }
    
    return {
        "github": github_status,
        "linkedin": linkedin_status,
        "user_found": True
    }
