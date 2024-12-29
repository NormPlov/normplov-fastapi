from sqlalchemy import Column, Integer, ForeignKey, DateTime, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class CareerCategoryLink(Base):
    __tablename__ = "career_category_links"

    id = Column(Integer, primary_key=True, index=True)
    career_id = Column(Integer, ForeignKey("careers.id", ondelete="CASCADE"), nullable=False)
    career_category_id = Column(Integer, ForeignKey("career_categories.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    # Relationships
    career = relationship("Career", back_populates="career_category_links")
    career_category = relationship("CareerCategory", back_populates="career_category_links")