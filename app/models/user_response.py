import uuid

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.core.database import Base
from sqlalchemy.sql import func


class UserResponse(Base):
    __tablename__ = "user_responses"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    assessment_type_id = Column(Integer, ForeignKey("assessment_types.id", ondelete="CASCADE"), nullable=False)
    user_test_id = Column(Integer, ForeignKey("user_tests.id", ondelete="CASCADE"), nullable=False)
    draft_name = Column(String, nullable=True)
    response_data = Column(JSONB, nullable=False)
    is_draft = Column(Boolean, default=False)
    is_deleted = Column(Boolean, default=False)
    is_completed = Column(Boolean, default=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=True, onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="responses")
    assessment_type = relationship("AssessmentType", back_populates="user_responses")
    user_test = relationship("UserTest", back_populates="user_responses")



