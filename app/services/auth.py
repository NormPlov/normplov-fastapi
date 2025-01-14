import uuid
import logging
import secrets
import string

from fastapi import HTTPException, status
from datetime import datetime
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt, JWTError
from fastapi.responses import JSONResponse
from datetime import timedelta
from passlib.context import CryptContext
from sqlalchemy.orm import selectinload
from sqlalchemy.orm import joinedload
from app.core.config import settings
from app.exceptions.formatters import format_http_exception
from app.models.user import User
from app.schemas.payload import BaseResponse
from app.schemas.user import UserCreateRequest, VerifyResetPasswordRequest, VerifyResetPasswordResponse
from app.utils.email import send_verification_email
from app.utils.security import generate_verification_code, generate_reset_code
from app.utils.password import hash_password, validate_password, validate_and_hash_password
from app.models.role import Role
from app.models.user_role import UserRole
from app.services.token import create_access_token, create_refresh_token

logger = logging.getLogger(__name__)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def generate_random_password(length: int = 12) -> str:

    characters = string.ascii_letters + string.digits + string.punctuation
    password = ''.join(secrets.choice(characters) for _ in range(length))

    return password


# async def get_or_create_user(db: AsyncSession, user_info: dict) -> dict:
#     email = user_info.get("email")
#     name = user_info.get("name") or ""
#     picture = user_info.get("picture", "")
#     if isinstance(picture, dict):
#         picture = picture.get("data", {}).get("url", "")
#
#     if not email:
#         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email is required.")
#
#     stmt = select(User).options(selectinload(User.roles).joinedload(UserRole.role)).where(User.email == email)
#     result = await db.execute(stmt)
#     user = result.scalars().first()
#
#     if not user:
#         raw_password = generate_random_password()
#         hashed_password = hash_password(raw_password)
#         user = User(
#             uuid=str(uuid.uuid4()),
#             username=name,
#             email=email,
#             avatar=picture,
#             password=hashed_password,
#             is_verified=True,
#             is_active=True,
#         )
#         db.add(user)
#         await db.commit()
#         await db.refresh(user)
#
#         stmt = select(Role).where(Role.name == "USER")
#         result = await db.execute(stmt)
#         default_role = result.scalars().first()
#
#         if not default_role:
#             raise HTTPException(
#                 status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#                 detail="Default role 'USER' not found in the database."
#             )
#
#         user_role = UserRole(user_id=user.id, role_id=default_role.id)
#         db.add(user_role)
#         await db.commit()
#
#         stmt = select(User).options(selectinload(User.roles).joinedload(UserRole.role)).where(User.id == user.id)
#         result = await db.execute(stmt)
#         user = result.scalars().first()
#
#     user_roles = [user_role.role.name for user_role in user.roles if user_role.role] if user.roles else []
#
#     access_token = create_access_token(data={"sub": user.uuid})
#     refresh_token = create_refresh_token(data={"sub": user.uuid})
#
#     return {
#         "payload": user,
#         "payload": {
#             "uuid": user.uuid,
#             "username": user.username,
#             "email": user.email,
#             "avatar": user.avatar,
#             "roles": user_roles,
#             "access_token": access_token,
#             "refresh_token": refresh_token,
#             "token_type": "bearer",
#         }
#     }

async def get_or_create_user(db: AsyncSession, user_info: dict) -> dict:
    email = user_info.get("email")
    name = user_info.get("name", "")
    picture = user_info.get("picture", "")
    if isinstance(picture, dict):
        picture = picture.get("data", {}).get("url", "")

    if not email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email is required.")

    stmt = select(User).options(selectinload(User.roles).joinedload(UserRole.role)).where(User.email == email)
    result = await db.execute(stmt)
    user = result.scalars().first()

    if not user:
        raw_password = generate_random_password()
        hashed_password = hash_password(raw_password)
        user = User(
            uuid=str(uuid.uuid4()),
            username=name,
            email=email,
            avatar=picture,
            password=hashed_password,
            is_verified=True,
            is_active=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

        stmt = select(Role).where(Role.name == "USER")
        result = await db.execute(stmt)
        default_role = result.scalars().first()

        if not default_role:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Default role 'USER' not found in the database."
            )

        user_role = UserRole(user_id=user.id, role_id=default_role.id)
        db.add(user_role)
        await db.commit()

        stmt = select(User).options(selectinload(User.roles).joinedload(UserRole.role)).where(User.id == user.id)
        result = await db.execute(stmt)
        user = result.scalars().first()

    user_roles = [user_role.role.name for user_role in user.roles if user_role.role] if user.roles else []

    return {
        "uuid": user.uuid,
        "username": user.username,
        "email": user.email,
        "avatar": user.avatar,
        "roles": user_roles,
    }


async def validate_user_credentials(db: AsyncSession, email: str, password: str) -> User:
    try:
        stmt = (
            select(User)
            .where(User.email == email)
            .options(joinedload(User.roles))
        )
        result = await db.execute(stmt)
        user = result.scalars().first()

        if not user:
            raise format_http_exception(
                status_code=status.HTTP_401_UNAUTHORIZED,
                message="Incorrect email or password."
            )

        if not pwd_context.verify(password, user.password):
            raise format_http_exception(
                status_code=status.HTTP_401_UNAUTHORIZED,
                message="Incorrect email or password."
            )

        if not user.is_verified:
            raise format_http_exception(
                status_code=status.HTTP_403_FORBIDDEN,
                message="User is not verified. Please verify your account."
            )

        if not user.is_active:
            raise format_http_exception(
                status_code=status.HTTP_403_FORBIDDEN,
                message="User account is inactive. Please contact support."
            )

        return user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating user credentials for email {email}: {e}")
        raise format_http_exception(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="An unexpected error occurred while validating user credentials.",
            details=str(e),
        )


async def perform_login(db: AsyncSession, email: str, password: str) -> BaseResponse:
    user = await validate_user_credentials(db, email, password)

    if not user.is_active:
        raise format_http_exception(
            status_code=status.HTTP_403_FORBIDDEN,
            message="User account is inactive. Contact support."
        )
    if not user.is_verified:
        raise format_http_exception(
            status_code=status.HTTP_403_FORBIDDEN,
            message="User account is not verified. Please verify your email."
        )

    stmt = (
        select(Role.name)
        .join(UserRole, Role.id == UserRole.role_id)
        .where(UserRole.user_id == user.id, UserRole.is_deleted == False)
    )
    result = await db.execute(stmt)
    user_roles = [row.name for row in result.all()]

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": str(user.uuid),
            "name": user.username,
            "email": user.email,
            "roles": user_roles,
        },
        expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(
        data={
            "sub": str(user.uuid),
            "name": user.username,
            "email": user.email,
            "roles": user_roles,
        }
    )

    return BaseResponse(
        date=datetime.utcnow().strftime("%d-%B-%Y"),
        status=status.HTTP_200_OK,
        message=f"Welcome back, {user.username}! Login successful 🎉",
        payload={
            "uuid": user.uuid,
            "username": user.username,
            "email": user.email,
            "roles": user_roles,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        }
    )


async def generate_new_access_token(refresh_token: str, db: AsyncSession) -> BaseResponse:
    try:
        # Decode the refresh token
        payload = jwt.decode(refresh_token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        user_uuid = payload.get("sub")

        if user_uuid is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token payload: missing user identifier."
            )

        stmt = (
            select(User)
            .options(joinedload(User.roles).joinedload(UserRole.role))  # Eagerly load roles
            .where(User.uuid == user_uuid)
        )

        async with db.begin():
            result = await db.execute(stmt)
            user = result.scalars().first()

        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive."
            )

        user_roles = [role.role.name for role in user.roles] if user.roles else []

        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={
                "sub": str(user.uuid),
                "name": user.username,
                "email": user.email,
                "roles": user_roles,
            },
            expires_delta=access_token_expires,
        )
        refresh_token = create_refresh_token(
            data={
                "sub": str(user.uuid),
                "name": user.username,
                "email": user.email,
                "roles": user_roles,
            }
        )

        return BaseResponse(
            date=datetime.utcnow().strftime("%d-%B-%Y"),
            status=status.HTTP_200_OK,
            message="New access token generated successfully.",
            payload={
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer"
            }
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token."
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


async def generate_password_reset_code(email: str, db: AsyncSession) -> BaseResponse:
    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User with this email does not exist."
        )

    reset_code = generate_reset_code()
    expiration_time = datetime.utcnow() + timedelta(hours=1)
    user.reset_password_code = reset_code
    user.reset_password_code_expiration = expiration_time
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return BaseResponse(
        date=datetime.utcnow().strftime("%d-%B-%Y"),
        status=status.HTTP_200_OK,
        message="Password reset code generated successfully.",
        payload={"email": user.email, "reset_code": reset_code}
    )


async def reset_user_password(email: str, reset_code: str, new_password: str, db: AsyncSession) -> BaseResponse:
    # Fetch the user by email
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

    return BaseResponse(
        date=datetime.utcnow().strftime("%d-%B-%Y"),
        status=status.HTTP_200_OK,
        message="Password reset successfully. Please log in with your new password.",
        payload={"email": user.email}
    )


async def verify_reset_password(
    data: VerifyResetPasswordRequest,
    db: AsyncSession
) -> VerifyResetPasswordResponse:
    try:
        logger.info(f"Verifying reset password code for email: {data.email}")

        # Retrieve the user by email
        stmt = select(User).where(User.email == data.email)
        result = await db.execute(stmt)
        user = result.scalars().first()

        if not user:
            logger.warning(f"User not found with email: {data.email}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User with this email does not exist.",
            )

        # Validate reset code and expiration
        if not user.reset_password_code:
            logger.warning(f"No reset code found for user: {data.email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No reset code is associated with this user.",
            )

        if user.reset_password_code != data.reset_code:
            logger.warning(f"Invalid reset code for user: {data.email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid reset code.",
            )

        if user.reset_password_code_expiration < datetime.utcnow():
            logger.warning(f"Expired reset code for user: {data.email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reset code has expired.",
            )

        logger.info(f"Reset password code verified successfully for email: {data.email}")

        return VerifyResetPasswordResponse(
            date=datetime.utcnow().strftime("%d-%B-%Y"),
            status=status.HTTP_200_OK,
            message="Reset password code verified successfully.",
            payload={"email": data.email},
        )

    except HTTPException as http_error:
        logger.warning(f"HTTP Exception during verification: {http_error.detail}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during verification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during reset password verification.",
        )


async def resend_reset_password_code(email: str, db: AsyncSession) -> BaseResponse:

    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User with this email does not exist."
        )

    reset_code = generate_reset_code()
    expiration_time = datetime.utcnow() + timedelta(minutes=15)

    user.reset_password_code = reset_code
    user.reset_password_code_expiration = expiration_time
    user.updated_at = datetime.utcnow()

    try:
        db.add(user)
        await db.commit()
        await db.refresh(user)
    except Exception as e:
        logger.error(f"Error while resending reset password code: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resend reset password code: {str(e)}"
        )

    # Send the reset password email
    await send_verification_email(user.email, user.username, reset_code)

    return BaseResponse(
        date=datetime.utcnow().strftime("%d-%B-%Y"),
        status=status.HTTP_200_OK,
        message="Reset password code resent successfully.",
        payload={"email": user.email, "reset_code": reset_code}
    )


async def verify_user(email: str, verification_code: str, db: AsyncSession) -> BaseResponse:
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

    return BaseResponse(
        date=datetime.utcnow().strftime("%d-%B-%Y"),
        status=status.HTTP_200_OK,
        message="User verified successfully.",
        payload={"email": user.email}
    )


def verify_password_reset_code(user: User, reset_code: str) -> bool:
    return (
            user.reset_password_code == reset_code
            and user.reset_password_code_expiration > datetime.utcnow()
    )


def generate_code_expiration(minutes: int) -> datetime:
    return datetime.utcnow() + timedelta(minutes=minutes)


async def resend_verification_code(email: str, db: AsyncSession) -> BaseResponse:
    user = await get_user_by_email(email, db)

    if user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already verified."
        )

    new_verification_code = generate_verification_code()
    expiration_time = generate_code_expiration(minutes=15)

    user.verification_code = new_verification_code
    user.verification_code_expiration = expiration_time
    user.updated_at = datetime.utcnow()

    try:
        db.add(user)
        await db.commit()
        await db.refresh(user)
    except Exception as e:
        logger.error(f"Error while resending verification code: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resend verification code: {str(e)}"
        )

    return BaseResponse(
        date=datetime.utcnow().strftime("%d-%B-%Y"),
        status=status.HTTP_200_OK,
        message="Verification code resent successfully.",
        payload={
            "email": user.email,
            "verification_code": new_verification_code,
            "username": user.username
        }
    )


async def get_user_by_email(email: str, db: AsyncSession) -> User:
    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )

    return user


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
        max_age=30 * 24 * 60 * 60,
    )


def unset_jwt_cookies(response: JSONResponse):
    response.delete_cookie("access_token", httponly=True)
    response.delete_cookie("refresh_token", httponly=True)


async def register_new_user(create_user: UserCreateRequest, db: AsyncSession) -> BaseResponse:
    if create_user.password != create_user.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match."
        )

    hashed_password = validate_and_hash_password(create_user.password)

    stmt = select(User).where(User.email == create_user.email)
    result = await db.execute(stmt)
    if result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered."
        )

    verification_code = generate_verification_code()
    expiration_time = datetime.utcnow() + timedelta(minutes=3)

    new_user = User(
        uuid=str(uuid.uuid4()),
        username=create_user.username,
        email=create_user.email,
        password=hashed_password,
        verification_code=verification_code,
        verification_code_expiration=expiration_time,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    await assign_user_role(new_user.id, "USER", db)

    # Send the verification email
    await send_verification_email(new_user.email, new_user.username, verification_code)

    return BaseResponse(
        date=datetime.utcnow().strftime("%d-%B-%Y"),
        status=status.HTTP_201_CREATED,
        message="User registered successfully. Please verify your email.",
        payload={"email": new_user.email}
    )


async def assign_user_role(user_id: int, role_name: str, db: AsyncSession) -> None:
    stmt = select(Role).where(Role.name == role_name)
    result = await db.execute(stmt)
    role = result.scalars().first()

    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role '{role_name}' not found."
        )

    user_role = UserRole(
        user_id=user_id,
        role_id=role.id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    db.add(user_role)
    await db.commit()

