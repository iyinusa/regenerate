from datetime import datetime
import uuid
from typing import Optional

from sqlalchemy import String, DateTime, ForeignKey, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.session import Base

class ProfilePrivacy(Base):
    __tablename__ = "rg_profile_privacy"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("rg_users.id"), unique=True, index=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    # Stores which sections to hide, e.g., {"chronicles": true, "experience": false}
    # True means hidden, False (or missing key) means visible
    hidden_sections: Mapped[Optional[dict]] = mapped_column(JSON, default=dict, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user: Mapped["User"] = relationship("User", back_populates="privacy_settings")
