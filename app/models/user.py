from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String, nullable=False)
    username = Column(String(100), unique=True, index=True)
    email = Column(String(255), unique=True, index=True)
    password = Column(String(100))
    avatar = Column(String(255), nullable=False, default="")
    address = Column(Text, nullable=False, default="")
    phone_number = Column(String(20), nullable=False, default="")
    bio = Column(Text, nullable=False, default="")
    gender = Column(String(10), nullable=False, default="")
    date_of_birth = Column(DateTime, nullable=True)

    # User status
    is_active = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=False)
    is_deleted = Column(Boolean, default=False)
    is_blocked = Column(Boolean, default=False)

    # Verification and password reset fields
    verification_code = Column(String, nullable=True)
    verification_code_expiration = Column(DateTime, nullable=True)
    reset_password_code = Column(String, nullable=True)
    reset_password_code_expiration = Column(DateTime, nullable=True)

    # Timestamp fields
    verified_at = Column(DateTime, nullable=True, default=None)
    registered_at = Column(DateTime, nullable=True, default=None)
    updated_at = Column(DateTime, nullable=True, onupdate=func.now())
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    # Relationship with UserRole
    roles = relationship("UserRole", back_populates="user", cascade="all, delete-orphan")
    responses = relationship("UserResponse", back_populates="user", cascade="all, delete-orphan")
    scores = relationship("UserAssessmentScore", back_populates="user", cascade="all, delete-orphan")
    ai_recommendations = relationship("AIRecommendation", back_populates="user", cascade="all, delete-orphan")
    tests = relationship("UserTest", back_populates="user", cascade="all, delete-orphan")
    feedbacks = relationship("UserFeedback", back_populates="user", cascade="all, delete-orphan")
