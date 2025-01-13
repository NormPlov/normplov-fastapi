import uuid

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base


class UserTest(Base):
    __tablename__ = "user_tests"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    assessment_type_id = Column(Integer, ForeignKey("assessment_types.id", ondelete="CASCADE"), nullable=False)
    is_completed = Column(Boolean, default=False, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User", back_populates="tests")
    user_responses = relationship("UserResponse", back_populates="user_test", cascade="all, delete-orphan")
    user_scores = relationship("UserAssessmentScore", back_populates="user_test", cascade="all, delete-orphan")
    assessment_type = relationship("AssessmentType", back_populates="user_tests")
    feedbacks = relationship("UserFeedback", back_populates="user_test", cascade="all, delete-orphan")
    test_references = relationship(
        "UserTestReference", back_populates="user_test", cascade="all, delete-orphan"
    )
