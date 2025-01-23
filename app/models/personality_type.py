from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from ..core.database import Base


class PersonalityType(Base):
    __tablename__ = "personality_types"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(36), unique=True, nullable=False)
    name = Column(String(100), unique=True, nullable=False)
    title = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    career_personality_types = relationship(
        "CareerPersonalityType", back_populates="personality_type"
    )
    characteristics = relationship(
        "PersonalityCharacteristic",
        back_populates="personality_type",
        cascade="all, delete-orphan",
    )
    strengths = relationship(
        "PersonalityStrength",
        back_populates="personality_type",
        cascade="all, delete-orphan",
    )
    weaknesses = relationship(
        "PersonalityWeakness",
        back_populates="personality_type",
        cascade="all, delete-orphan",
    )
