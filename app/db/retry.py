"""
Database retry utilities for handling transient connection failures.
"""

from __future__ import annotations

import asyncio
from functools import wraps
from typing import Any, Callable, TypeVar

from sqlalchemy.exc import DBAPIError, OperationalError
from app.core.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


async def retry_on_db_error(
    func: Callable[..., T],
    max_retries: int = 3,
    initial_delay: float = 0.5,
    backoff_factor: float = 2.0,
    *args: Any,
    **kwargs: Any,
) -> T:
    """
    Retry a database operation with exponential backoff.
    
    This is critical for Cloud Run where connections can become stale
    due to instance pausing/resuming or network issues.
    
    Args:
        func: Async function to retry
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay between retries in seconds
        backoff_factor: Multiplier for delay after each retry
        *args: Positional arguments to pass to func
        **kwargs: Keyword arguments to pass to func
        
    Returns:
        Result of the function call
        
    Raises:
        Last exception if all retries fail
    """
    delay = initial_delay
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            return await func(*args, **kwargs)
        except (OperationalError, DBAPIError) as e:
            last_exception = e
            error_msg = str(e)
            
            # Check if it's a connection-related error
            is_connection_error = any(
                phrase in error_msg.lower()
                for phrase in [
                    "closed",
                    "lost connection",
                    "can't connect",
                    "connection refused",
                    "timeout",
                    "broken pipe",
                    "transport",
                ]
            )
            
            if not is_connection_error or attempt >= max_retries - 1:
                # Not a connection error or final attempt - raise immediately
                raise
            
            logger.warning(
                f"Database operation failed (attempt {attempt + 1}/{max_retries}): {error_msg}. "
                f"Retrying in {delay:.2f}s..."
            )
            
            await asyncio.sleep(delay)
            delay *= backoff_factor
    
    # This should never be reached, but just in case
    if last_exception:
        raise last_exception
    raise RuntimeError("Retry loop completed without success or exception")


def with_db_retry(
    max_retries: int = 3,
    initial_delay: float = 0.5,
    backoff_factor: float = 2.0,
):
    """
    Decorator to automatically retry database operations on connection errors.
    
    Usage:
        @with_db_retry(max_retries=3)
        async def get_user(db: AsyncSession, user_id: int):
            result = await db.execute(select(User).where(User.id == user_id))
            return result.scalar_one_or_none()
    
    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay between retries in seconds
        backoff_factor: Multiplier for delay after each retry
        
    Returns:
        Decorated function with retry logic
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            return await retry_on_db_error(
                func,
                max_retries=max_retries,
                initial_delay=initial_delay,
                backoff_factor=backoff_factor,
                *args,
                **kwargs,
            )
        return wrapper
    return decorator
