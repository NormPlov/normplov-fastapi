from sqlalchemy import Column, Integer, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class ValueCategoryKeyImprovement(Base):
    __tablename__ = "value_category_key_improvements"

    id = Column(Integer, primary_key=True, index=True)
    value_category_id = Column(Integer, ForeignKey("value_categories.id"), nullable=False)
    improvement_text = Column(Text, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    value_category = relationship("ValueCategory", back_populates="key_improvements")
