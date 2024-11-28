from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from ..core.database import Base


class PersonalityTrait(Base):
    __tablename__ = "personality_traits"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(36), unique=True, nullable=False)
    personality_type_id = Column(Integer, ForeignKey("personality_types.id", ondelete="CASCADE"), nullable=False)
    trait = Column(String(255), nullable=False)
    is_positive = Column(Boolean, nullable=False)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    personality_type = relationship("PersonalityType", back_populates="traits")
