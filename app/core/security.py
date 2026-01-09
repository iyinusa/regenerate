"""
Security utilities for authentication and password handling.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta
from typing import Any

from jose import JWTError, jwt

from app.core.config import settings

# Use bcrypt directly to avoid passlib initialization issues
import bcrypt


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hashed password with optimized performance.
    
    Args:
        plain_password: Plain text password
        hashed_password: Hashed password to verify against
        
    Returns:
        bool: True if password matches, False otherwise
    """
    # Truncate password to 72 bytes if necessary
    if len(plain_password.encode('utf-8')) > 72:
        plain_password = plain_password.encode('utf-8')[:72].decode('utf-8', errors='ignore')
    
    try:
        # Use bcrypt directly with better error handling
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except (ValueError, TypeError):
        # Handle invalid hash formats gracefully
        return False


def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt with optimized rounds for performance.
    
    Args:
        password: Plain text password to hash
        
    Returns:
        str: Hashed password
    """
    # Bcrypt has a 72-byte limit, truncate if necessary
    if len(password.encode('utf-8')) > 72:
        password = password.encode('utf-8')[:72].decode('utf-8', errors='ignore')
    
    # Use bcrypt with 10 rounds (instead of default 12) for better performance
    # while maintaining good security for web applications
    salt = bcrypt.gensalt(rounds=10)
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: Data to encode in the token
        expires_delta: Optional custom expiration time
        
    Returns:
        str: Encoded JWT token
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expires_min)
    
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_alg)
    
    return encoded_jwt


def create_refresh_token(data: dict[str, Any]) -> str:
    """
    Create a JWT refresh token with longer expiration.
    
    Args:
        data: Data to encode in the token (usually just user ID)
        
    Returns:
        str: Encoded JWT refresh token
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.refresh_token_expires_days)
    
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_alg)
    
    return encoded_jwt


def create_game_session_token(data: dict[str, Any]) -> str:
    """
    Create a JWT token for active game sessions with extended expiration.
    
    Args:
        data: Data to encode in the token (user ID + game context)
        
    Returns:
        str: Encoded JWT game session token
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.game_session_token_expires_min)
    
    to_encode.update({"exp": expire, "type": "game_session"})
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_alg)
    
    return encoded_jwt


def decode_access_token(token: str) -> dict[str, Any] | None:
    """
    Decode and verify a JWT access token.
    
    Args:
        token: JWT token to decode
        
    Returns:
        dict | None: Decoded token payload, or None if invalid
    """
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_alg])
        return payload
    except JWTError:
        return None


def decode_token(token: str, expected_type: str | None = None) -> dict[str, Any] | None:
    """
    Decode and verify any JWT token with optional type validation.
    
    Args:
        token: JWT token to decode
        expected_type: Expected token type ("access", "refresh", "game_session")
        
    Returns:
        dict | None: Decoded token payload, or None if invalid
    """
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_alg])
        
        # Validate token type if specified
        if expected_type and payload.get("type") != expected_type:
            return None
            
        return payload
    except JWTError:
        return None
