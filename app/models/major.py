import uuid

from sqlalchemy import Column, Integer, String, Boolean, Enum, DateTime, Float, Text, func, UUID
from sqlalchemy.orm import relationship
from enum import Enum as PyEnum
from ..core.database import Base


class DegreeType(PyEnum):
    ASSOCIATE = "ASSOCIATE"
    BACHELOR = "BACHELOR"
    MASTER = "MASTER"
    PHD = "PHD"


class Major(Base):
    __tablename__ = "majors"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)
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
    careers = relationship("CareerMajor", back_populates="major", cascade="all, delete-orphan")
