from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base
import uuid


class TestDraft(Base):
    __tablename__ = "test_drafts"

    id = Column(Integer, primary_key=True, index=True)  # Internal primary key
    uuid = Column(String, unique=True, nullable=False, default=lambda: str(uuid.uuid4()))  # Public identifier
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    assessment_type_id = Column(Integer, ForeignKey("assessment_types.id", ondelete="CASCADE"), nullable=True)
    draft_data = Column(JSON, nullable=False, default={})
    is_completed = Column(Boolean, default=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=True, onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="test_drafts")
    assessment_type = relationship("AssessmentType", back_populates="test_drafts")
