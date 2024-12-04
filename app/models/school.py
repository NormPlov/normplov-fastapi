import uuid
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, Text, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from enum import Enum as PyEnum
from app.core.database import Base


class SchoolType(PyEnum):
    PRIVATE = "PRIVATE"
    PUBLIC = "PUBLIC"
    TVET = "TVET"
    MAJORS_COURSES = "MAJORS_COURSES"


class School(Base):
    __tablename__ = "schools"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)
    kh_name = Column(String, nullable=False)
    en_name = Column(String, nullable=False)
    type = Column(Enum(SchoolType, name="school_type"), nullable=True)
    logo_url = Column(String, nullable=True)
    cover_image = Column(String, nullable=True)
    location = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    lowest_price = Column(Float, nullable=True)
    highest_price = Column(Float, nullable=True)
    map = Column(String, nullable=True)
    email = Column(String, nullable=True)
    website = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    mission = Column(Text, nullable=True)
    vision = Column(Text, nullable=True)
    is_deleted = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    majors = relationship("SchoolMajor", back_populates="school", cascade="all, delete-orphan")
    faculties = relationship("Faculty", back_populates="school", cascade="all, delete-orphan")
