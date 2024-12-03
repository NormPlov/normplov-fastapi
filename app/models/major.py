import uuid

from sqlalchemy import Column, Integer, String, Boolean, Enum, DateTime, Float, Text, func
from sqlalchemy.orm import relationship
from enum import Enum as PyEnum
from ..core.database import Base


class DegreeType(PyEnum):
    ASSOCIATE = "Associate"
    BACHELOR = "Bachelor"
    MASTER = "Master"
    PHD = "PhD"


class Major(Base):
    __tablename__ = "majors"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String, unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    fee_per_year = Column(Float, nullable=True)
    duration_years = Column(Integer, nullable=True)
    is_popular = Column(Boolean, default=False, nullable=False)
    degree = Column(Enum(DegreeType), nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    school_majors = relationship("SchoolMajor", back_populates="major", cascade="all, delete-orphan")
