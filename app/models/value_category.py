from datetime import datetime

from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime
from sqlalchemy.orm import relationship
from app.core.database import Base


class ValueCategory(Base):
    __tablename__ = "value_categories"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String, unique=True, nullable=False)
    name = Column(String(100), nullable=False, unique=True)
    definition = Column(Text, nullable=False)
    characteristics = Column(Text, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    careers = relationship("Career", back_populates="value_category")
