from sqlalchemy import Column, Integer, String, Boolean, DateTime, func, UUID
from sqlalchemy.orm import relationship
from app.core.database import Base
import uuid


class Province(Base):
    __tablename__ = "provinces"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)
    name = Column(String, nullable=False, unique=True)
    is_deleted = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    schools = relationship("School", back_populates="province")
    # jobs = relationship("Job", back_populates="province")
