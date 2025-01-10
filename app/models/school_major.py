from sqlalchemy import Column, Integer, Boolean, DateTime, func, ForeignKey
from sqlalchemy.orm import relationship
from ..core.database import Base


class SchoolMajor(Base):
    __tablename__ = "school_majors"

    school_id = Column(Integer, ForeignKey("schools.id"), primary_key=True)
    major_id = Column(Integer, ForeignKey("majors.id"), primary_key=True)
    is_deleted = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    school = relationship("School", back_populates="majors")
    major = relationship("Major", back_populates="school_majors")
