from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from uuid import uuid4
from app.core.database import Base


class LearningStyleTechniqueImage(Base):
    __tablename__ = "learning_style_technique_images"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String, unique=True, nullable=False, default=lambda: str(uuid4()))
    learning_style_technique_id = Column(
        Integer, ForeignKey("learning_style_study_techniques.id", ondelete="CASCADE"), nullable=False
    )
    file_name = Column(String, nullable=False)
    file_url = Column(String, nullable=False)
    file_type = Column(String, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=True, onupdate=func.now())

    # Relationships
    technique = relationship("LearningStyleStudyTechnique", back_populates="images")
