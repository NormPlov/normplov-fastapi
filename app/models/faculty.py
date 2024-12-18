import uuid
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..core.database import Base


class Faculty(Base):
    __tablename__ = "faculties"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    school_id = Column(Integer, ForeignKey("schools.id", ondelete="CASCADE"), nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    school = relationship("School", back_populates="faculties")
    majors = relationship("Major", back_populates="faculty", cascade="all, delete-orphan")
