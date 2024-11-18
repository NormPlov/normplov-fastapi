from sqlalchemy import Column, Integer, ForeignKey, Float, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base



class UserAssessmentScore(Base):
    __tablename__ = "user_assessment_scores"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    assessment_type_id = Column(Integer, ForeignKey("assessment_types.id", ondelete="CASCADE"), nullable=False)
    dimension_id = Column(Integer, ForeignKey("dimensions.id", ondelete="CASCADE"), nullable=False)
    score = Column(Float, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="scores")
    assessment_type = relationship("AssessmentType", back_populates="user_scores")
    dimension = relationship("Dimension", back_populates="scores")
