from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    ForeignKey,
    DateTime,
    Text,
    func,
)
from sqlalchemy.orm import relationship
from app.core.database import Base
import uuid

class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String, unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    industry = Column(String(255), nullable=True)
    location = Column(Text, nullable=True)
    type = Column(String(50), default="Full-time", nullable=False)
    position = Column(String(255), nullable=True)
    qualification = Column(String(255), nullable=True)
    published_date = Column(DateTime, nullable=True)
    description = Column(Text, nullable=True)
    requirements = Column(Text, nullable=True)
    resources = Column(Text, nullable=True)
    job_category_id = Column(Integer, ForeignKey("job_categories.id", ondelete="SET NULL"), nullable=True)
    is_scraped = Column(Boolean, default=False, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=True, onupdate=func.now())

    # Relationships
    job_category = relationship("JobCategory", back_populates="jobs")
    images = relationship("JobImage", back_populates="job")

