import uuid

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class Career(Base):
    __tablename__ = "careers"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String, unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    personality_type_id = Column(Integer, ForeignKey("personality_types.id", ondelete="SET NULL"), nullable=True)
    holland_code_id = Column(Integer, ForeignKey("holland_codes.id", ondelete="SET NULL"), nullable=True)
    value_category_id = Column(Integer, ForeignKey("value_categories.id", ondelete="SET NULL"), nullable=True)
    is_deleted = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=True, onupdate=func.now())

    # Relationships
    personality_type = relationship("PersonalityType", back_populates="careers")
    holland_code = relationship("HollandCode", back_populates="careers")
    dimension_careers = relationship("DimensionCareer", back_populates="career")
    value_category = relationship("ValueCategory", back_populates="careers")
    majors = relationship("CareerMajor", back_populates="career", cascade="all, delete-orphan")
