from sqlalchemy import Column, Integer, String, Boolean, Text, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

import uuid

class AssessmentType(Base):
    __tablename__ = "assessment_types"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String, unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, nullable=True)

    # Relationships
    dimensions = relationship("Dimension", back_populates="assessment_type", cascade="all, delete-orphan")
    user_responses = relationship("UserResponse", back_populates="assessment_type", cascade="all, delete-orphan")
    user_scores = relationship("UserAssessmentScore", back_populates="assessment_type", cascade="all, delete-orphan")
    test_drafts = relationship("TestDraft", back_populates="assessment_type", cascade="all, delete-orphan")
