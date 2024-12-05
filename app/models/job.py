import uuid
from sqlalchemy.orm import relationship
from app.core.database import Base
from sqlalchemy import Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey,
    DateTime,
    Text,
    Boolean,
    func,
)


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)
    type = Column(Enum("Full-time", "Part-time", "Contract", "Internship", "Temporary", name="job_type"),
                  default="Full-time", nullable=False)
    position = Column(String(255), nullable=True)
    qualification = Column(String(255), nullable=True)
    published_date = Column(DateTime, nullable=True)
    description = Column(Text, nullable=True)
    responsibilities = Column(Text, nullable=True)
    requirements = Column(Text, nullable=True)
    resources = Column(Text, nullable=True)
    job_category_id = Column(Integer, ForeignKey("job_categories.id", ondelete="SET NULL"), nullable=True)
    province_id = Column(Integer, ForeignKey("provinces.id", ondelete="SET NULL"), nullable=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="SET NULL"), nullable=True)
    is_scraped = Column(Boolean, default=False, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=True, onupdate=func.now())

    # Relationships
    job_category = relationship("JobCategory", back_populates="jobs")
    province = relationship("Province", back_populates="jobs")
    company = relationship("Company", back_populates="jobs")
    images = relationship("JobImage", back_populates="job")
