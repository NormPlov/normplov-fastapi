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
    is_deleted = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=True, onupdate=func.now())

    # Relationships
    dimension_careers = relationship("DimensionCareer", back_populates="career")
    majors = relationship("CareerMajor", back_populates="career", cascade="all, delete-orphan")
    personality_types = relationship("CareerPersonalityType", back_populates="career", cascade="all, delete-orphan")
    holland_codes = relationship("CareerHollandCode", back_populates="career", cascade="all, delete-orphan")
    value_categories = relationship("CareerValueCategory", back_populates="career", cascade="all, delete-orphan")
    career_category_links = relationship("CareerCategoryLink", back_populates="career", cascade="all, delete-orphan")