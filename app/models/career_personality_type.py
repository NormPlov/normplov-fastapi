from sqlalchemy import Column, Integer, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class CareerPersonalityType(Base):
    __tablename__ = "career_personality_types"

    id = Column(Integer, primary_key=True, index=True)
    career_id = Column(Integer, ForeignKey("careers.id", ondelete="CASCADE"), nullable=False)
    personality_type_id = Column(Integer, ForeignKey("personality_types.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    # Relationships
    career = relationship("Career", back_populates="personality_types")
    personality_type = relationship("PersonalityType", back_populates="career_personality_types")
