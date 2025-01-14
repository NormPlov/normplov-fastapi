import uuid

from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class CareerCategory(Base):
    __tablename__ = "career_categories"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String, unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=True, onupdate=func.now())

    # Relationship
    career_category_links = relationship("CareerCategoryLink", back_populates="career_category", cascade="all, delete-orphan")
    responsibilities = relationship(
        "CareerCategoryResponsibility",
        back_populates="career_category",
        cascade="all, delete-orphan",
    )
    requirements = relationship(
        "CareerCategoryRequirement",
        back_populates="career_category",
        cascade="all, delete-orphan",
    )