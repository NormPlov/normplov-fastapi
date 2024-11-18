from fastapi import HTTPException, status
from datetime import datetime, timedelta
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt, JWTError
import uuid
from passlib.context import CryptContext
from ..core.config import settings
from ..models.user import User
from ..schemas.user import UserCreateRequestDto
from app.utils.security import get_password_hash, generate_verification_code, generate_reset_code
from ..services.token import create_access_token
from ..utils.password_utils import hash_password
from ..models.role import Role
from ..models.user_role import UserRole

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def generate_new_access_token(refresh_token: str, db: AsyncSession) -> dict:
    try:
        # Decode the refresh token
        payload = jwt.decode(refresh_token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        email = payload.get("sub")

        if email is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Query the user by email
        stmt = select(User).where(User.email == email)
        result = await db.execute(stmt)
        user = result.scalars().first()

        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Generate a new access token
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": email},
            expires_delta=access_token_expires
        )

        return {"access_token": access_token, "token_type": "bearer"}

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )



async def generate_password_reset_code(email: str, db: AsyncSession) -> tuple[User, str]:
    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User with this email does not exist.😯"
        )

    # Generate the reset code and expiration time
    reset_code = generate_reset_code()
    expiration_time = datetime.utcnow() + timedelta(hours=1)

    # Update the user record
    user.reset_password_code = reset_code
    user.reset_password_code_expiration = expiration_time
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return user, reset_code


# Verify Password Reset Code
def verify_password_reset_code(user: User, reset_code: str) -> bool:
    # Check if the reset code matches and is not expired
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

    # Verify the reset code
    if not await verify_password_reset_code(user, reset_code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset code."
        )

    # Update the user's password
    user.password = hash_password(new_password)
    user.reset_password_code = None
    user.reset_password_code_expiration = None
    user.updated_at = datetime.utcnow()

    db.add(user)
    await db.commit()
    await db.refresh(user)

    return user



def generate_code_expiration(minutes: int) -> datetime:
    return datetime.utcnow() + timedelta(minutes=minutes)


async def generate_and_save_verification_code(email: str, db: AsyncSession):
    # Check if the user exists
    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    if user.is_verified:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User is already verified.")

    # Generate a new verification code and expiration time
    new_verification_code = generate_verification_code()
    expiration_time = generate_code_expiration(minutes=15)

    # Update the user with the new code and expiration
    user.verification_code = new_verification_code
    user.verification_code_expiration = expiration_time
    user.updated_at = datetime.utcnow()

    # Save changes to the database
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return user, new_verification_code


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



async def register_new_user(create_user: UserCreateRequestDto, db: AsyncSession) -> User:
    if create_user.password != create_user.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match 😒",
        )

    # Check if the email already exists
    stmt = select(User).where(User.email == create_user.email)
    result = await db.execute(stmt)
    if result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered 🤔",
        )

    # Generate verification code and expiration
    verification_code = generate_verification_code()
    expiration_time = generate_code_expiration(minutes=15)

    # Create a new user
    new_user = User(
        uuid=str(uuid.uuid4()),
        username=create_user.username,
        email=create_user.email,
        password=get_password_hash(create_user.password),
        verification_code=verification_code,
        verification_code_expiration=expiration_time,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

    # Save the new user to the database
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    # Assign the USER role to the new user
    stmt = select(Role).where(Role.name == "USER")
    result = await db.execute(stmt)
    user_role = result.scalars().first()

    if not user_role:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Default USER role not found. Please contact support."
        )

    # Create UserRole entry
    new_user_role = UserRole(user_id=new_user.id, role_id=user_role.id)
    db.add(new_user_role)
    await db.commit()

    return new_user

