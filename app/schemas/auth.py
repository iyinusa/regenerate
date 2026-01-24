"""
Authentication schemas for user registration, login, and token management.
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Dict, Any
from datetime import datetime


class UserRegistrationSchema(BaseModel):
    """Schema for user registration."""
    username: str = Field(..., min_length=3, max_length=50, description="Username")
    email: EmailStr = Field(..., description="Email address")
    password: str = Field(..., min_length=8, description="Password")
    full_name: Optional[str] = Field(None, max_length=255, description="Full name")


class UserLoginSchema(BaseModel):
    """Schema for user login."""
    email: EmailStr = Field(..., description="Email address")
    password: str = Field(..., description="Password")


class TokenSchema(BaseModel):
    """Schema for JWT tokens."""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration in seconds")


class TokenRefreshSchema(BaseModel):
    """Schema for token refresh."""
    refresh_token: str = Field(..., description="Refresh token")


class UserProfileSchema(BaseModel):
    """Schema for user profile information."""
    id: str = Field(..., description="User ID")
    username: Optional[str] = Field(None, description="Username")
    email: Optional[str] = Field(None, description="Email")
    full_name: Optional[str] = Field(None, description="Full name")
    is_active: bool = Field(..., description="Is user active")
    is_verified: bool = Field(..., description="Is user verified")
    created_at: datetime = Field(..., description="Creation timestamp")
    
    # OAuth status
    github_connected: bool = Field(default=False, description="GitHub OAuth connected")
    linkedin_connected: bool = Field(default=False, description="LinkedIn OAuth connected")
    github_username: Optional[str] = Field(None, description="GitHub username")


class AuthStatusSchema(BaseModel):
    """Schema for authentication status."""
    authenticated: bool = Field(..., description="Is user authenticated")
    user: Optional[UserProfileSchema] = Field(None, description="User profile")
    guest_id: str = Field(..., description="Guest ID")


class OAuthLinkSchema(BaseModel):
    """Schema for linking OAuth accounts."""
    provider: str = Field(..., description="OAuth provider (github/linkedin)")
    redirect_url: str = Field(..., description="OAuth authorization URL")


class UserUpdateSchema(BaseModel):
    """Schema for user profile update."""
    full_name: Optional[str] = Field(None, max_length=255, description="Full name")
    email: Optional[EmailStr] = Field(None, description="Email address")


class PasswordChangeSchema(BaseModel):
    """Schema for password change."""
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, description="New password")