from fastapi import HTTPException, status, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.user import User
from app.schemas.user import UserResponseDto, UpdateUserDto
from jose import jwt, JWTError
from app.core.config import settings
from app.utils.verify import is_valid_uuid
from datetime import datetime
from app.utils.password_utils import (
    hash_password,
    verify_password
)
import shutil



async def get_current_user_service(token: str, db: AsyncSession) -> UserResponseDto:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        email = payload.get("sub")

        if email is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        stmt = select(User).where(User.email == email)
        result = await db.execute(stmt)
        user = result.scalars().first()

        if not user or user.is_deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found.",
            )

        return UserResponseDto(
            uuid=user.uuid,
            username=user.username,
            email=user.email,
            avatar=user.avatar,
            address=user.address,
            phone_number=user.phone_number,
            bio=user.bio,
            gender=user.gender,
            date_of_birth=user.date_of_birth,
            is_deleted=user.is_deleted,
            is_active=user.is_active,
            is_verified=user.is_verified,
            registered_at=user.registered_at,
        )

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def change_user_password(uuid: str, old_password: str, new_password: str, db: AsyncSession):
    stmt = select(User).where(User.uuid == uuid)
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

    user.password = hash_password(new_password)
    user.updated_at = datetime.utcnow()

    db.add(user)
    await db.commit()
    await db.refresh(user)

    return {"message": "Password updated successfully"}


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


async def update_user_profile(uuid: str, profile_update: UpdateUserDto, db: AsyncSession):
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



async def update_user_by_uuid(uuid: str, user_update: UpdateUserDto, session: AsyncSession):
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
        UserResponseDto(
            uuid=user.uuid,
            username=user.username,
            email=user.email,
            avatar=user.avatar,
            address=user.address,
            phone_number=user.phone_number,
            bio=user.bio,
            gender=user.gender,
            date_of_birth=user.date_of_birth,
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

    return UserResponseDto(
        uuid=user.uuid,
        username=user.username,
        email=user.email,
        avatar=user.avatar,
        address=user.address,
        phone_number=user.phone_number,
        bio=user.bio,
        gender=user.gender,
        date_of_birth=user.date_of_birth,
        is_deleted=user.is_deleted,
        is_active=user.is_active,
        is_verified=user.is_verified,
        registered_at=user.registered_at
    )
