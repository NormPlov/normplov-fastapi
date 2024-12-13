import uuid

from sqlalchemy.orm import relationship

from app.core.database import Base
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Text,
    Boolean,
    func,
    ARRAY, ForeignKey,
)


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(UUID, unique=True, nullable=False, default=uuid.uuid4)
    job_category_id = Column(Integer, ForeignKey("job_categories.id"), nullable=True)
    title = Column(String(255), nullable=False)
    company = Column(String(255), nullable=False)
    logo = Column(Text, nullable=True)
    facebook_url = Column(Text, nullable=True)
    location = Column(String(255), nullable=True)
    posted_at = Column(DateTime, nullable=True)
    description = Column(Text, nullable=True)
    category = Column(String(255), nullable=True)
    job_type = Column(String(50), nullable=True)
    schedule = Column(String(255), nullable=True)
    salary = Column(String(50), nullable=True)
    closing_date = Column(DateTime, nullable=True)
    requirements = Column(ARRAY(Text), nullable=True)
    responsibilities = Column(ARRAY(Text), nullable=True)
    benefits = Column(ARRAY(Text), nullable=True)
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    website = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_scraped = Column(Boolean, default=False, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=True, onupdate=func.now())

    # Relationships
    job_category = relationship("JobCategory", back_populates="jobs")
