from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.core.database import Base


class HollandCode(Base):
    __tablename__ = "holland_codes"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String, unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    code = Column(String(10), nullable=False)
    type = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    key_traits = relationship("HollandKeyTrait", back_populates="holland_code", cascade="all, delete-orphan")
    careers = relationship("Career", back_populates="holland_code", cascade="all, delete-orphan")


