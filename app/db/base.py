"""
Base module for importing all models.
This is used by Alembic for migrations.
"""

from app.db.session import Base
from app.models.user import User, ProfileHistory

# Import all models here to ensure they are registered with SQLAlchemy

__all__ = ["Base", "User", "ProfileHistory"]
