from sqlalchemy import Column, Integer, String, ForeignKey, Text, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from uuid import uuid4
from app.core.database import Base


class LearningStyleStudyTechnique(Base):
    __tablename__ = "learning_style_study_techniques"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String, unique=True, nullable=False, default=lambda: str(uuid4()))
    dimension_id = Column(Integer, ForeignKey("dimensions.id", ondelete="CASCADE"), nullable=False)
    category = Column(String, nullable=False)
    technique_name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    is_deleted = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=True, onupdate=func.now())

    # Relationships
    dimension = relationship("Dimension", back_populates="learning_style_techniques")
    images = relationship(
        "LearningStyleTechniqueImage",
        back_populates="technique",
        cascade="all, delete-orphan"
    )

