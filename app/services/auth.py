from sqlalchemy.orm import Session
from fastapi import HTTPException, status, BackgroundTasks
from datetime import datetime, timedelta
from jose import jwt

from app.core.config import settings
from app.models.user import User
from app.schemas.user import UserCreateRequest
from app.core.security import get_password_hash, generate_verification_code, generate_reset_code
from app.utils.email_utils import send_verification_email


# Create Password Reset Code
def create_password_reset_code(user: User, db: Session) -> str:
    # Generate a 6-digit numeric code
    reset_code = generate_reset_code()
    expiration_time = datetime.utcnow() + timedelta(hours=1)

    # Update the user's reset code and expiration
    user.reset_password_code = reset_code
    user.reset_password_code_expiration = expiration_time
    db.commit()
    db.refresh(user)

    return reset_code


# Verify Password Reset Code
def verify_password_reset_code(user: User, reset_code: str) -> bool:
    # Check if the reset code matches and is not expired
    if user.reset_password_code == reset_code and user.reset_password_code_expiration > datetime.utcnow():
        return True
    return False


# Reset Password
def reset_password(user: User, new_password: str, db: Session):
    user.password = new_password
    user.reset_password_code = None
    user.reset_password_code_expiration = None
    db.commit()
    db.refresh(user)


def generate_code_expiration(minutes: int) -> datetime:
    return datetime.utcnow() + timedelta(minutes=minutes)


def resend_verification_code(email: str, db: Session, background_tasks: BackgroundTasks):
    user = db.query(User).filter(User.email == email).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    if user.is_verified:
        raise HTTPException(status_code=400, detail="User is already verified.")

    # Generate a new verification code and expiration time
    new_verification_code = generate_verification_code()
    expiration_time = generate_code_expiration(minutes=15)

    # Update the user with the new code and expiration
    user.verification_code = new_verification_code
    user.verification_code_expiration = expiration_time
    user.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(user)

    # Send the verification code via email
    background_tasks.add_task(
        send_verification_email,
        email=user.email,
        username=user.username,
        verification_code=new_verification_code
    )

    return {"message": "Verification code resent successfully"}


def verify_user(email: str, verification_code: str, db: Session):
    user = db.query(User).filter(User.email == email).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    if user.is_verified:
        raise HTTPException(status_code=400, detail="User is already verified.")

    if user.verification_code != verification_code or user.verification_code_expiration < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Invalid or expired verification code.")

    # Mark the user as verified and active
    user.is_verified = True
    user.is_active = True
    user.verification_code = None
    user.verification_code_expiration = None
    user.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(user)

    return {"message": "User verified successfully"}


def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta if expires_delta else timedelta(minutes=15))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    expire = datetime.utcnow() + timedelta(days=7)
    to_encode = data.copy()
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

 
def authenticate_user(db: Session, username: str, password: str):
    user = db.query(User).filter(User.username == username).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not verified. Please verify your account.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive. Please contact support.",
        )

    return user


async def register_user(data: UserCreateRequest, db: Session, background_tasks: BackgroundTasks):
    existing_user = db.query(User).filter(
        (User.email == data.email) | (User.username == data.username)
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=422,
            detail="Username or email is already registered."
        )

    verification_code = generate_verification_code()
    expiration_time = generate_code_expiration(minutes=15)

    new_user = User(
        username=data.username,
        email=data.email,
        password=get_password_hash(data.password),
        verification_code=verification_code,
        verification_code_expiration=expiration_time,
        is_active=False,
        is_verified=False,
        registered_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    background_tasks.add_task(
        send_verification_email,
        email=new_user.email,
        username=new_user.username,
        verification_code=verification_code
    )

    return new_user

