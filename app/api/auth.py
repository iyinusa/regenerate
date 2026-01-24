"""Authentication Routes for Username/Password and OAuth.

This module handles comprehensive authentication including:
- Username/password registration and login with JWT tokens
- OAuth 2.0 authentication flows for GitHub and LinkedIn
- Token refresh and user session management
- Profile data extraction and enrichment
"""

import logging
import secrets
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from urllib.parse import urlencode
import uuid

import httpx
from fastapi import APIRouter, HTTPException, status, Depends, Query, Request, Header
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, or_

from app.core.config import settings
from app.core.security import (
    create_access_token, create_refresh_token, 
    get_password_hash, verify_password
)
from app.core.dependencies import get_current_user, get_current_user_required, verify_refresh_token
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    UserRegistrationSchema, UserLoginSchema, TokenSchema, TokenRefreshSchema,
    UserProfileSchema, AuthStatusSchema, OAuthLinkSchema, PasswordChangeSchema,
    UserUpdateSchema
)

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/auth", tags=["authentication"])

# In-memory state storage (use Redis in production)
_oauth_states: Dict[str, Dict[str, Any]] = {}


# Helper functions
def get_guest_id_from_request(guest_id_header: Optional[str] = None) -> str:
    """Get or generate guest ID from request."""
    if guest_id_header:
        return guest_id_header
    return str(uuid.uuid4())


async def create_user_tokens(user: User, db: AsyncSession) -> TokenSchema:
    """Create access and refresh tokens for user."""
    token_data = {"sub": user.id, "email": user.email, "username": user.username}
    
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token({"sub": user.id})
    
    # Store refresh token in database
    await db.execute(
        update(User)
        .where(User.id == user.id)
        .values(refresh_token=refresh_token)
    )
    await db.commit()
    
    return TokenSchema(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.access_token_expires_min * 60
    )


# =============================================================================
# Username/Password Authentication
# =============================================================================

@router.post(
    "/register",
    response_model=TokenSchema,
    summary="Register New User",
    description="Register a new user account with username, email and password. Username will be used for profile URLs."
)
async def register_user(
    user_data: UserRegistrationSchema,
    x_guest_id: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
):
    """Register a new user account."""
    
    # Check if username or email already exists
    result = await db.execute(
        select(User).where(
            or_(User.username == user_data.username, User.email == user_data.email)
        )
    )
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        if existing_user.username == user_data.username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
    
    # Get or generate guest ID
    guest_id = get_guest_id_from_request(x_guest_id)
    
    # Check if guest user exists and update it
    result = await db.execute(select(User).where(User.guest_id == guest_id))
    user = result.scalar_one_or_none()
    
    password_hash = get_password_hash(user_data.password)
    
    if user:
        # Update existing guest user with registration data
        await db.execute(
            update(User)
            .where(User.id == user.id)
            .values(
                username=user_data.username,
                email=user_data.email,
                full_name=user_data.full_name,
                password_hash=password_hash,
                is_verified=True
            )
        )
        await db.commit()
        
        # Refresh user object
        await db.refresh(user)
    else:
        # Create new user
        user = User(
            guest_id=guest_id,
            username=user_data.username,
            email=user_data.email,
            full_name=user_data.full_name,
            password_hash=password_hash,
            is_verified=True
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    
    return await create_user_tokens(user, db)


@router.post(
    "/login",
    response_model=TokenSchema,
    summary="User Login",
    description="Login with email and password."
)
async def login_user(
    credentials: UserLoginSchema,
    db: AsyncSession = Depends(get_db)
):
    """Login user with email and password."""
    
    # Find user by email
    result = await db.execute(
        select(User).where(User.email == credentials.email)
    )
    user = result.scalar_one_or_none()
    
    if not user or not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    if not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is inactive"
        )
    
    return await create_user_tokens(user, db)


@router.post(
    "/refresh",
    response_model=TokenSchema,
    summary="Refresh Access Token",
    description="Refresh access token using refresh token."
)
async def refresh_token(
    token_data: TokenRefreshSchema,
    db: AsyncSession = Depends(get_db)
):
    """Refresh access token."""
    user = await verify_refresh_token(token_data.refresh_token, db)
    return await create_user_tokens(user, db)


@router.post(
    "/logout",
    summary="User Logout",
    description="Logout user and invalidate refresh token."
)
async def logout_user(
    current_user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db)
):
    """Logout user and invalidate refresh token."""
    await db.execute(
        update(User)
        .where(User.id == current_user.id)
        .values(refresh_token=None)
    )
    await db.commit()
    
    return {"message": "Successfully logged out"}


@router.get(
    "/me",
    response_model=UserProfileSchema,
    summary="Get Current User",
    description="Get current authenticated user profile."
)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user_required)
):
    """Get current user profile."""
    return UserProfileSchema(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        created_at=current_user.created_at,
        github_connected=bool(current_user.github_access_token),
        linkedin_connected=bool(current_user.linkedin_access_token),
        github_username=current_user.github_username
    )


@router.get(
    "/status",
    response_model=AuthStatusSchema,
    summary="Get Authentication Status",
    description="Get current authentication status and user information."
)
async def get_auth_status(
    x_guest_id: Optional[str] = Header(None),
    current_user: Optional[User] = Depends(get_current_user),
):
    """Get authentication status."""
    guest_id = get_guest_id_from_request(x_guest_id)
    
    if current_user:
        return AuthStatusSchema(
            authenticated=True,
            guest_id=current_user.guest_id,
            user=UserProfileSchema(
                id=current_user.id,
                username=current_user.username,
                email=current_user.email,
                full_name=current_user.full_name,
                is_active=current_user.is_active,
                is_verified=current_user.is_verified,
                created_at=current_user.created_at,
                github_connected=bool(current_user.github_access_token),
                linkedin_connected=bool(current_user.linkedin_access_token),
                github_username=current_user.github_username
            )
        )
    
    return AuthStatusSchema(
        authenticated=False,
        guest_id=guest_id,
        user=None
    )


@router.put(
    "/profile",
    response_model=UserProfileSchema,
    summary="Update User Profile",
    description="Update user profile information (requires authentication)."
)
async def update_user_profile(
    user_data: UserUpdateSchema,
    current_user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db)
):
    """Update user profile."""
    
    # If email is being changed, check if it's already taken
    if user_data.email and user_data.email != current_user.email:
        result = await db.execute(
            select(User).where(User.email == user_data.email)
        )
        existing_user = result.scalar_one_or_none()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
    
    update_data = user_data.dict(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No data provided for update"
        )
        
    await db.execute(
        update(User)
        .where(User.id == current_user.id)
        .values(**update_data)
    )
    await db.commit()
    await db.refresh(current_user)
    
    return UserProfileSchema(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        created_at=current_user.created_at,
        github_connected=bool(current_user.github_access_token),
        linkedin_connected=bool(current_user.linkedin_access_token),
        github_username=current_user.github_username
    )


@router.post(
    "/change-password",
    summary="Change Password",
    description="Change user password (requires authentication)."
)
async def change_password(
    password_data: PasswordChangeSchema,
    current_user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db)
):
    """Change user password."""
    if not current_user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No password set for this account"
        )
    
    if not verify_password(password_data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    new_password_hash = get_password_hash(password_data.new_password)
    
    await db.execute(
        update(User)
        .where(User.id == current_user.id)
        .values(password_hash=new_password_hash, refresh_token=None)  # Invalidate all tokens
    )
    await db.commit()
    
    return {"message": "Password changed successfully"}


# =============================================================================
# OAuth Integration
# =============================================================================


def generate_oauth_state(identifier: str, provider: str, user_type: str = "guest") -> str:
    """Generate a secure OAuth state parameter.
    
    Args:
        identifier: User or guest identifier
        provider: OAuth provider name
        user_type: Type of user (guest, user)
        
    Returns:
        Unique state string
    """
    state = secrets.token_urlsafe(32)
    _oauth_states[state] = {
        "identifier": identifier,
        "provider": provider,
        "user_type": user_type,
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
    response_model=OAuthLinkSchema,
    summary="Initiate GitHub OAuth",
    description="Start the GitHub OAuth flow for repository access and profile enrichment."
)
async def github_oauth_start(
    guest_id: Optional[str] = Query(None, description="Guest user ID for linking OAuth (for unauthenticated users)"),
    x_guest_id: Optional[str] = Header(None),
    current_user: Optional[User] = Depends(get_current_user)
):
    """Start GitHub OAuth flow.
    
    Works for both authenticated users and guests.
    """
    if not settings.github_client_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GitHub OAuth is not configured"
        )
    
    if current_user:
        # Authenticated user
        state = generate_oauth_state(current_user.id, "github", "user")
    else:
        # Guest user
        identifier = guest_id or get_guest_id_from_request(x_guest_id)
        state = generate_oauth_state(identifier, "github", "guest")
    
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
    
    return OAuthLinkSchema(provider="github", redirect_url=auth_url)


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
    """Handle GitHub OAuth callback for both authenticated users and guests."""
    
    # Verify state
    state_data = verify_oauth_state(state)
    if not state_data:
        logger.warning("Invalid or expired OAuth state")
        return RedirectResponse(
            url=f"{settings.base_url}/?error=invalid_state",
            status_code=status.HTTP_302_FOUND
        )
    
    identifier = state_data["identifier"]
    user_type = state_data["user_type"]
    
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
            full_name = github_user.get("name")
            email = github_user.get("email")
            
            # Update user record based on user type
            if user_type == "user":
                # Authenticated user - update by user ID
                result = await db.execute(select(User).where(User.id == identifier))
            else:
                # Guest user - find or create by guest_id
                result = await db.execute(select(User).where(User.guest_id == identifier))
            
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
                        full_name=user.full_name or full_name,
                        email=user.email or email,
                    )
                )
                await db.commit()
                logger.info(f"Updated user {user.id} with GitHub OAuth credentials")
            elif user_type == "guest":
                # Create new user record for guest
                user = User(
                    guest_id=identifier,
                    github_id=github_id,
                    github_username=github_username,
                    github_access_token=access_token,
                    github_scopes=scopes,
                    full_name=full_name,
                    email=email,
                )
                db.add(user)
                await db.commit()
                logger.info(f"Created new user for guest_id: {identifier}")
            else:
                logger.warning(f"User not found for identifier: {identifier}")
                return RedirectResponse(
                    url=f"{settings.base_url}/?error=user_not_found",
                    status_code=status.HTTP_302_FOUND
                )
            
            # If this was a guest who now has OAuth, they might want to create an account
            redirect_params = f"github_connected=true&username={github_username}"
            if user_type == "guest" and not user.password_hash:
                redirect_params += "&suggest_register=true"
            
            return RedirectResponse(
                url=f"{settings.base_url}/?{redirect_params}",
                status_code=status.HTTP_302_FOUND
            )
            
    except Exception as e:
        logger.error(f"GitHub OAuth callback error: {e}")
        return RedirectResponse(
            url=f"{settings.base_url}/?error=oauth_failed",
            status_code=status.HTTP_302_FOUND
        )


# =============================================================================
# LinkedIn OAuth
# =============================================================================

@router.get(
    "/linkedin",
    response_model=OAuthLinkSchema,
    summary="Initiate LinkedIn OAuth",
    description="Start the LinkedIn OAuth flow for profile access."
)
async def linkedin_oauth_start(
    guest_id: Optional[str] = Query(None, description="Guest user ID for linking OAuth (for unauthenticated users)"),
    x_guest_id: Optional[str] = Header(None),
    current_user: Optional[User] = Depends(get_current_user)
):
    """Start LinkedIn OAuth flow.
    
    Works for both authenticated users and guests.
    """
    if not settings.linkedin_client_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LinkedIn OAuth is not configured"
        )
    
    if current_user:
        # Authenticated user
        state = generate_oauth_state(current_user.id, "linkedin", "user")
    else:
        # Guest user
        identifier = guest_id or get_guest_id_from_request(x_guest_id)
        state = generate_oauth_state(identifier, "linkedin", "guest")
    
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
    
    return OAuthLinkSchema(provider="linkedin", redirect_url=auth_url)


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
    """Handle LinkedIn OAuth callback for both authenticated users and guests."""
    
    # Verify state
    state_data = verify_oauth_state(state)
    if not state_data:
        logger.warning("Invalid or expired OAuth state")
        return RedirectResponse(
            url=f"{settings.base_url}/?error=invalid_state",
            status_code=status.HTTP_302_FOUND
        )
    
    identifier = state_data["identifier"]
    user_type = state_data["user_type"]
    
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
                headers={"Authorization": f"Bearer {access_token}"}
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
            
            # Update user record based on user type
            if user_type == "user":
                # Authenticated user - update by user ID
                result = await db.execute(select(User).where(User.id == identifier))
            else:
                # Guest user - find or create by guest_id
                result = await db.execute(select(User).where(User.guest_id == identifier))
            
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
            elif user_type == "guest":
                # Create new user record for guest
                user = User(
                    guest_id=identifier,
                    linkedin_id=linkedin_id,
                    linkedin_access_token=access_token,
                    linkedin_token_expires_at=token_expires_at,
                    full_name=full_name,
                    email=email,
                )
                db.add(user)
                await db.commit()
                logger.info(f"Created new user for guest_id: {identifier}")
            else:
                logger.warning(f"User not found for identifier: {identifier}")
                return RedirectResponse(
                    url=f"{settings.base_url}/?error=user_not_found",
                    status_code=status.HTTP_302_FOUND
                )
            
            # If this was a guest who now has OAuth, they might want to create an account
            redirect_params = "linkedin_connected=true"
            if user_type == "guest" and not user.password_hash:
                redirect_params += "&suggest_register=true"
            
            return RedirectResponse(
                url=f"{settings.base_url}/?{redirect_params}",
                status_code=status.HTTP_302_FOUND
            )
    except Exception as e:
        logger.error(f"LinkedIn OAuth callback error: {e}")
        return RedirectResponse(
            url=f"{settings.base_url}/?error=oauth_failed",
            status_code=status.HTTP_302_FOUND
        )


# =============================================================================
# OAuth Status Endpoints (Legacy - for backward compatibility)
# =============================================================================

@router.get(
    "/github/status",
    summary="Check GitHub OAuth Status",
    description="Check if a user has connected their GitHub account (legacy endpoint)."
)
async def github_oauth_status(
    guest_id: Optional[str] = Query(None, description="Guest user ID"),
    current_user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Check GitHub OAuth connection status."""
    
    if current_user:
        user = current_user
    elif guest_id:
        result = await db.execute(select(User).where(User.guest_id == guest_id))
        user = result.scalar_one_or_none()
    else:
        return {"connected": False, "message": "No user or guest ID provided"}
    
    if not user:
        return {"connected": False, "message": "User not found"}
    
    if user.github_access_token:
        return {
            "connected": True,
            "username": user.github_username,
            "scopes": user.github_scopes,
        }
    
    return {"connected": False}


@router.get(
    "/linkedin/status",
    summary="Check LinkedIn OAuth Status",
    description="Check if a user has connected their LinkedIn account (legacy endpoint)."
)
async def linkedin_oauth_status(
    guest_id: Optional[str] = Query(None, description="Guest user ID"),
    current_user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Check LinkedIn OAuth connection status."""
    
    if current_user:
        user = current_user
    elif guest_id:
        result = await db.execute(select(User).where(User.guest_id == guest_id))
        user = result.scalar_one_or_none()
    else:
        return {"connected": False, "message": "No user or guest ID provided"}
    
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
    "/oauth/status",
    summary="Get All OAuth Status",
    description="Get the OAuth connection status for all providers (legacy endpoint)."
)
async def get_all_oauth_status(
    guest_id: Optional[str] = Query(None, description="Guest user ID"),
    current_user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get OAuth status for all providers."""
    
    if current_user:
        user = current_user
    elif guest_id:
        result = await db.execute(select(User).where(User.guest_id == guest_id))
        user = result.scalar_one_or_none()
    else:
        return {
            "github": {"connected": False},
            "linkedin": {"connected": False},
            "user_found": False
        }
    
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
