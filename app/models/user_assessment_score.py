from sqlalchemy import Column, Integer, ForeignKey, DateTime, Boolean, String
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base
from sqlalchemy.dialects.postgresql import JSONB
import uuid

class UserAssessmentScore(Base):
    __tablename__ = "user_assessment_scores"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String, unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    assessment_type_id = Column(Integer, ForeignKey("assessment_types.id", ondelete="CASCADE"), nullable=False)
    dimension_id = Column(Integer, ForeignKey("dimensions.id", ondelete="CASCADE"), nullable=False)
    score = Column(JSONB, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=True, onupdate=func.now())

    user = relationship("User", back_populates="scores")
    assessment_type = relationship("AssessmentType", back_populates="user_scores")
    dimension = relationship("Dimension", back_populates="scores")
