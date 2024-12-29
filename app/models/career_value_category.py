from sqlalchemy import Column, Integer, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class CareerValueCategory(Base):
    __tablename__ = "career_value_categories"

    id = Column(Integer, primary_key=True, index=True)
    career_id = Column(Integer, ForeignKey("careers.id", ondelete="CASCADE"), nullable=False)
    value_category_id = Column(Integer, ForeignKey("value_categories.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    # Relationships
    career = relationship("Career", back_populates="value_categories")
    value_category = relationship("ValueCategory", back_populates="career_value_categories")
