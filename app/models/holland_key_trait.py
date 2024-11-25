from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class HollandKeyTrait(Base):
    __tablename__ = "holland_key_traits"

    id = Column(Integer, primary_key=True, index=True)
    holland_code_id = Column(Integer, ForeignKey("holland_codes.id", ondelete="CASCADE"), nullable=False)
    key_trait = Column(String(100), nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    holland_code = relationship("HollandCode", back_populates="key_traits")
