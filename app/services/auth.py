from fastapi import HTTPException, status
from datetime import datetime
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt, JWTError
from fastapi.responses import JSONResponse
from datetime import timedelta
from passlib.context import CryptContext
import uuid
import logging
from ..core.config import settings
from ..models.user import User
from ..schemas.user import UserCreateRequest, UserResponse
from ..utils.security import generate_verification_code, generate_reset_code
from ..utils.password_utils import hash_password, validate_password, verify_password, validate_and_hash_password
from ..models.role import Role
from ..models.user_role import UserRole
from ..services.token import create_access_token


logger = logging.getLogger(__name__)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def get_or_create_user(db: AsyncSession, user_info: dict) -> User:
    email = user_info.get("email")
    name = user_info.get("name") or "Google User"
    picture = user_info.get("picture", "")

    if not email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email is required.")

    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    user = result.scalars().first()

    if not user:
        logger.info(f"Creating a new user for email: {email}")
        user = User(
            uuid=str(uuid.uuid4()),
            username=name,
            email=email,
            avatar=picture,
            is_verified=True,
            is_active=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    else:
        logger.info(f"User found for email: {email}")

    return user


async def generate_new_access_token(refresh_token: str, db: AsyncSession) -> dict:
    try:
        payload = jwt.decode(refresh_token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        user_uuid = payload.get("sub")

        if user_uuid is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token payload: missing user identifier.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        stmt = select(User).where(User.uuid == user_uuid)
        result = await db.execute(stmt)
        user = result.scalars().first()

        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": str(user.uuid)},
            expires_delta=access_token_expires
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "message": "New access token generated successfully.😍",
        }

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}",
        )


# Generate Password Reset Code
async def generate_password_reset_code(email: str, db: AsyncSession) -> tuple[User, str]:
    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User with this email does not exist.😯"
        )

    reset_code = generate_reset_code()
    expiration_time = datetime.utcnow() + timedelta(hours=1)
    user.reset_password_code = reset_code
    user.reset_password_code_expiration = expiration_time
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return user, reset_code


# Verify Password Reset Code
def verify_password_reset_code(user: User, reset_code: str) -> bool:
    if user.reset_password_code == reset_code and user.reset_password_code_expiration > datetime.utcnow():
        return True
    return False


# Reset Password
async def reset_user_password(email: str, reset_code: str, new_password: str, db: AsyncSession):
    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )

    if user.reset_password_code != reset_code or user.reset_password_code_expiration < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset code."
        )

    validate_password(new_password)
    user.password = hash_password(new_password)
    user.reset_password_code = None
    user.reset_password_code_expiration = None
    user.updated_at = datetime.utcnow()

    db.add(user)
    await db.commit()
    return {"message": "Password reset successfully!"}


def generate_code_expiration(minutes: int) -> datetime:
    return datetime.utcnow() + timedelta(minutes=minutes)


async def resend_verification_code(email: str, db: AsyncSession):
    user = await get_user_by_email(email, db)

    if user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already verified."
        )

    # Generate a new verification code and expiration time
    new_verification_code = generate_verification_code()
    expiration_time = generate_code_expiration(minutes=15)

    # Update user details
    user.verification_code = new_verification_code
    user.verification_code_expiration = expiration_time
    user.updated_at = datetime.utcnow()

    try:
        db.add(user)
        await db.commit()
        await db.refresh(user)
    except Exception as e:
        logger.error(f"Failed to save verification code for {email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save verification code."
        )

    return user, new_verification_code


async def get_user_by_email(email: str, db: AsyncSession):
    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )

    return user


async def verify_user(email: str, verification_code: str, db: AsyncSession):
    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    if user.is_verified:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User is already verified.")

    if user.verification_code != verification_code or user.verification_code_expiration < datetime.utcnow():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired verification code.")

    user.is_verified = True
    user.is_active = True
    user.verification_code = None
    user.verification_code_expiration = None
    user.updated_at = datetime.utcnow()

    db.add(user)
    await db.commit()
    await db.refresh(user)

    return {"message": "User verified successfully"}


def set_access_cookies(response: JSONResponse, access_token: str, refresh_token: str):
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        secure=True,
        samesite="Lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    response.set_cookie(
        key="refresh_token",
        value=f"Bearer {refresh_token}",
        httponly=True,
        secure=True,
        samesite="Lax",
        # Refresh token valid for 30 days
        max_age=30 * 24 * 60 * 60,
    )


def unset_jwt_cookies(response: JSONResponse):
    response.delete_cookie("access_token", httponly=True)
    response.delete_cookie("refresh_token", httponly=True)


async def validate_user_credentials(db: AsyncSession, email: str, password: str) -> User:
    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not pwd_context.verify(password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
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


async def register_new_user(create_user: UserCreateRequest, db: AsyncSession) -> User:

    if create_user.password != create_user.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match 😒",
        )

    hashed_password = validate_and_hash_password(create_user.password)

    stmt = select(User).where(User.email == create_user.email)
    result = await db.execute(stmt)
    if result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered 🤔",
        )

    verification_code = generate_verification_code()
    expiration_time = generate_code_expiration(minutes=15)

    new_user = User(
        uuid=str(uuid.uuid4()),
        username=create_user.username,
        email=create_user.email,
        password=hashed_password,
        verification_code=verification_code,
        verification_code_expiration=expiration_time,
        registered_at=datetime.utcnow(),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    user_role = await assign_user_role(new_user.id, "USER", db)

    if not user_role:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Default USER role not found. Please contact support.",
        )

    return new_user


async def assign_user_role(user_id: int, role_name: str, db: AsyncSession) -> UserRole:
    stmt = select(Role).where(Role.name == role_name)
    result = await db.execute(stmt)
    role = result.scalars().first()

    if not role:
        return None

    new_user_role = UserRole(user_id=user_id, role_id=role.id)
    db.add(new_user_role)
    await db.commit()
    return new_user_role
