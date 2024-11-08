from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from app.db.session import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, index=True)
    email = Column(String(255), unique=True, index=True)
    password = Column(String(100))

    # User status
    is_active = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=False)

    # Verification and password reset fields
    verification_code = Column(String, nullable=True)
    verification_code_expiration = Column(DateTime, nullable=True)
    reset_password_code = Column(String, nullable=True)
    reset_password_code_expiration = Column(DateTime, nullable=True)

    # Timestamp fields
    verified_at = Column(DateTime, nullable=True, default=None)
    registered_at = Column(DateTime, nullable=True, default=None)
    updated_at = Column(DateTime, nullable=True, default=None, onupdate=datetime.now)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
