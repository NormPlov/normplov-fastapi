import uuid

from sqlalchemy import Column, Integer, String, Boolean, Enum, DateTime, Float, Text, func, UUID, ForeignKey
from sqlalchemy.orm import relationship
from enum import Enum as PyEnum
from ..core.database import Base


class DegreeType(PyEnum):
    ASSOCIATE = "ASSOCIATE"
    BACHELOR = "BACHELOR"
    MASTER = "MASTER"
    PHD = "PHD"
    SHORT_COURSE = "SHORT_COURSE"


class Major(Base):
    __tablename__ = "majors"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    fee_per_year = Column(Float, nullable=True)
    duration_years = Column(Integer, nullable=True)
    is_popular = Column(Boolean, nullable=True)
    degree = Column(Enum(DegreeType), nullable=True)
    is_deleted = Column(Boolean, nullable=True)
    is_recommended = Column(Boolean, nullable=True)
    faculty_id = Column(Integer, ForeignKey("faculties.id", ondelete="CASCADE"), nullable=True)
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)

    # Relationships
    school_majors = relationship("SchoolMajor", back_populates="major", cascade="all, delete-orphan")
    careers = relationship("CareerMajor", back_populates="major", cascade="all, delete-orphan")
    faculty = relationship("Faculty", back_populates="majors")