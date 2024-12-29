from sqlalchemy import Column, Integer, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class CareerHollandCode(Base):
    __tablename__ = "career_holland_codes"

    id = Column(Integer, primary_key=True, index=True)
    career_id = Column(Integer, ForeignKey("careers.id", ondelete="CASCADE"), nullable=False)
    holland_code_id = Column(Integer, ForeignKey("holland_codes.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    # Relationships
    career = relationship("Career", back_populates="holland_codes")
    holland_code = relationship("HollandCode", back_populates="career_holland_codes")
