from sqlalchemy import Column, Integer, Boolean, DateTime, func, ForeignKey
from sqlalchemy.orm import relationship
from ..core.database import Base


class CareerMajor(Base):
    __tablename__ = "career_majors"

    career_id = Column(Integer, ForeignKey("careers.id", ondelete="CASCADE"), primary_key=True)
    major_id = Column(Integer, ForeignKey("majors.id", ondelete="CASCADE"), primary_key=True)
    is_deleted = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    career = relationship("Career", back_populates="majors")
    major = relationship("Major", back_populates="careers")
