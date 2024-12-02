from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey,
    DateTime,
    Text,
    JSON,
    func,
)
from sqlalchemy.orm import relationship
from app.core.database import Base
import uuid


class JobScrapingLog(Base):
    __tablename__ = "job_scraping_logs"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String, unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    source_url = Column(Text, nullable=False)
    scraped_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    total_scraped = Column(Integer, default=0, nullable=True)
    missing_data = Column(JSON, nullable=True)
    status = Column(String(50), default="Completed", nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=True, onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="scraping_logs", lazy="joined")
