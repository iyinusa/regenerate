from typing import Optional, List
from datetime import datetime
import uuid

from sqlalchemy import String, DateTime, ForeignKey, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.session import Base

class User(Base):
    __tablename__ = "rg_users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    guest_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), index=True, nullable=True)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # GitHub OAuth fields
    github_id: Mapped[Optional[str]] = mapped_column(String(255), unique=True, index=True, nullable=True)
    github_username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    github_access_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    github_token_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    github_scopes: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    
    # LinkedIn OAuth fields
    linkedin_id: Mapped[Optional[str]] = mapped_column(String(255), unique=True, index=True, nullable=True)
    linkedin_access_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    linkedin_token_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    linkedin_profile_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)

    profile_histories: Mapped[List["ProfileHistory"]] = relationship(back_populates="user", cascade="all, delete-orphan")

class ProfileHistory(Base):
    __tablename__ = "rg_profile_history"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("rg_users.id"), index=True)
    source_url: Mapped[str] = mapped_column(String(1024))
    raw_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    structured_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="profile_histories")
