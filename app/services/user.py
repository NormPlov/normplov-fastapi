import shutil
import logging

from fastapi import HTTPException, status, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt, JWTError
from sqlalchemy.future import select
from datetime import datetime
from ..core.config import settings
from ..models.user import User
from ..schemas.user import UserResponse, UpdateUser
from ..utils.format_date import format_date
from ..utils.password_utils import verify_password, validate_password, hash_password
from ..utils.verify import is_valid_uuid


logger = logging.getLogger(__name__)


async def block_user_service(uuid: str, is_blocked: bool, db: AsyncSession):

    stmt = select(User).where(User.uuid == uuid)
    result = await db.execute(stmt)
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    user.is_blocked = is_blocked
    user.updated_at = datetime.utcnow()

    db.add(user)
    await db.commit()
    await db.refresh(user)

    status = "blocked" if is_blocked else "unblocked"
    return {"message": f"User has been {status} successfully.", "uuid": user.uuid}


async def get_user_by_email(email: str, db: AsyncSession):
    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User with the given email not found."
        )

    return UserResponse(
        uuid=user.uuid,
        username=user.username,
        email=user.email,
        avatar=user.avatar,
        address=user.address,
        phone_number=user.phone_number,
        bio=user.bio,
        gender=user.gender,
        date_of_birth=format_date(user.date_of_birth),
        is_deleted=user.is_deleted,
        is_active=user.is_active,
        is_verified=user.is_verified,
        registered_at=user.registered_at or datetime.utcnow(),
    )


async def decode_jwt_token(token: str) -> str:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        user_uuid = payload.get("sub")
        if not user_uuid:
            raise ValueError("Missing user UUID in token payload")
        return user_uuid
    except JWTError as e:
        logger.error(f"JWT decoding failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def change_password(user_uuid: str, old_password: str, new_password: str, db: AsyncSession):
    stmt = select(User).where(User.uuid == user_uuid)
    result = await db.execute(stmt)
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )

    if not verify_password(old_password, user.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Old password is incorrect."
        )

    validate_password(new_password)
    user.password = hash_password(new_password)
    user.updated_at = datetime.utcnow()

    db.add(user)
    await db.commit()
    return {"message": "Password updated successfully!"}


async def update_user_bio(uuid: str, bio: str, db: AsyncSession):

    stmt = select(User).where(User.uuid == uuid)
    result = await db.execute(stmt)
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )

    user.bio = bio
    user.updated_at = datetime.utcnow()

    db.add(user)
    await db.commit()
    await db.refresh(user)

    return {
        "message": "User bio updated successfully.",
        "bio": user.bio,
    }


async def upload_profile_picture(uuid: str, file: UploadFile, db: AsyncSession):
    stmt = select(User).where(User.uuid == uuid)
    result = await db.execute(stmt)
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )

    file_location = f"uploads/profile_pictures/{uuid}_{file.filename}"
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    user.avatar = file_location
    user.updated_at = datetime.utcnow()

    db.add(user)
    await db.commit()
    await db.refresh(user)

    return {"message": "Profile picture updated successfully", "avatar_url": file_location}


async def update_user_profile(uuid: str, profile_update: UpdateUser, db: AsyncSession):
    stmt = select(User).where(User.uuid == uuid)
    result = await db.execute(stmt)
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )

    update_data = profile_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(user, key, value)

    user.updated_at = datetime.utcnow()

    db.add(user)
    await db.commit()
    await db.refresh(user)

    return user


async def delete_user_by_uuid(uuid: str, session: AsyncSession):
    if not is_valid_uuid(uuid):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user UUID.")

    stmt = select(User).where(User.uuid == uuid)
    result = await session.execute(stmt)
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    user.is_deleted = True
    user.updated_at = datetime.utcnow()

    session.add(user)
    await session.commit()
    await session.refresh(user)

    return {"message": f"User with UUID {uuid} has been marked as deleted."}


async def update_user_by_uuid(uuid: str, user_update: UpdateUser, session: AsyncSession):
    if not is_valid_uuid(uuid):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user UUID.")

    stmt = select(User).where(User.uuid == uuid)
    result = await session.execute(stmt)
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    # Apply updates
    update_data = user_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(user, key, value)

    user.updated_at = datetime.utcnow()

    session.add(user)
    await session.commit()
    await session.refresh(user)

    return {
        "message": "User updated successfully.",
        "user": {
            "uuid": user.uuid,
            "username": user.username,
            "email": user.email,
            "avatar": user.avatar,
            "address": user.address,
            "phone_number": user.phone_number,
            "bio": user.bio,
            "gender": user.gender,
            "date_of_birth": user.date_of_birth,
            "is_deleted": user.is_deleted,
            "is_active": user.is_active,
            "is_verified": user.is_verified,
            "registered_at": user.registered_at,
        }
    }


async def get_all_users(session: AsyncSession):

    query = select(User).where(User.is_deleted == False).order_by(User.created_at.desc())
    result = await session.execute(query)
    users = result.scalars().all()

    return [
        UserResponse(
            uuid=user.uuid,
            username=user.username,
            email=user.email,
            avatar=user.avatar,
            address=user.address,
            phone_number=user.phone_number,
            bio=user.bio,
            gender=user.gender,
            date_of_birth=format_date(user.date_of_birth),
            is_deleted=user.is_deleted,
            is_active=user.is_active,
            is_verified=user.is_verified,
            registered_at=user.registered_at
        )
        for user in users
    ]


async def get_user_by_uuid(uuid: str, session: AsyncSession):
    if not is_valid_uuid(uuid):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user UUID.")

    stmt = select(User).where(User.uuid == uuid)
    result = await session.execute(stmt)
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    return UserResponse(
        uuid=user.uuid,
        username=user.username,
        email=user.email,
        avatar=user.avatar,
        address=user.address,
        phone_number=user.phone_number,
        bio=user.bio,
        gender=user.gender,
        date_of_birth=format_date(user.date_of_birth),
        is_deleted=user.is_deleted,
        is_active=user.is_active,
        is_verified=user.is_verified,
        registered_at=user.registered_at
    )
