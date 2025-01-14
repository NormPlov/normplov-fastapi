import uuid

from sqlalchemy import Column, Integer, DateTime, func, ForeignKey, String, Text
from sqlalchemy.orm import relationship
from app.core.database import Base


class CareerCategoryRequirement(Base):
    __tablename__ = "career_category_requirements"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String, unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    career_category_id = Column(Integer, ForeignKey("career_categories.id", ondelete="CASCADE"), nullable=False)
    description = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=True, onupdate=func.now())

    # Relationships
    career_category = relationship("CareerCategory", back_populates="requirements")
