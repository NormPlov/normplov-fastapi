from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class StudyTechnique(Base):
    __tablename__ = "study_techniques"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(36), unique=True, nullable=False)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    category_id = Column(Integer, ForeignKey("technique_categories.id", ondelete="CASCADE"), nullable=False)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=None, onupdate=datetime.utcnow)
    image = Column(String, nullable=True)

    category = relationship("TechniqueCategory", back_populates="study_techniques")
    dimensions = relationship(
        "DimensionStudyTechnique", back_populates="study_technique", cascade="all, delete-orphan"
    )