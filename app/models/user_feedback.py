from sqlalchemy import Column, Integer, Text, Boolean, ForeignKey, DateTime, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import uuid


class UserFeedback(Base):
    __tablename__ = "user_feedbacks"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(UUID(as_uuid=True), unique=True, nullable=False, default=lambda: uuid.uuid4())
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    assessment_type_id = Column(Integer, ForeignKey("assessment_types.id", ondelete="CASCADE"), nullable=False)
    feedback = Column(Text, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
    is_promoted = Column(Boolean, default=False, nullable=False)  
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="feedbacks")
    assessment_type = relationship("AssessmentType", back_populates="feedbacks")