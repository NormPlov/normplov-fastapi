from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base
from sqlalchemy.dialects.postgresql import JSONB

class UserResponse(Base):
    __tablename__ = "user_responses"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String, unique=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    assessment_type_id = Column(Integer, ForeignKey("assessment_types.id", ondelete="CASCADE"), nullable=False)
    response_data = Column(JSONB, nullable=False)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=True, onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="responses")
    assessment_type = relationship("AssessmentType", back_populates="user_responses")
