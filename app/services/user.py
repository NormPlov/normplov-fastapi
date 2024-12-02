import shutil
import logging

from fastapi import HTTPException, status, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime
from app.models.user import User
from app.schemas.payload import BaseResponse
from app.schemas.user import UpdateUser, UserResponse
from app.utils.format_date import format_date
from app.utils.password import verify_password, validate_password, hash_password
from app.utils.verify import is_valid_uuid


logger = logging.getLogger(__name__)


async def block_user(uuid: str, is_blocked: bool, db: AsyncSession, current_user: User) -> BaseResponse:
    stmt = select(User).where(User.uuid == uuid)
    result = await db.execute(stmt)
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )

    if user.uuid == current_user.uuid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot block/unblock yourself."
        )

    if is_blocked and user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin users cannot be blocked."
        )

    user.is_blocked = is_blocked
    user.updated_at = datetime.utcnow()

    db.add(user)
    await db.commit()
    await db.refresh(user)

    return BaseResponse(
        date=datetime.utcnow().strftime("%d-%B-%Y"),
        status=status.HTTP_200_OK,
        message=f"User {'blocked' if is_blocked else 'unblocked'} successfully.",
        payload={
            "uuid": user.uuid,
            "username": user.username,
            "is_blocked": user.is_blocked,
        },
    )


async def get_user_by_email(email: str, db: AsyncSession, current_user: User) -> UserResponse:
    if current_user.email != email and not any(role.role.name == "ADMIN" for role in current_user.roles):
        raise HTTPException(status_code=403, detail="Permission denied.")

    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

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
        roles=[role.role.name for role in user.roles],
        is_deleted=user.is_deleted,
        is_active=user.is_active,
        is_verified=user.is_verified,
        registered_at=user.registered_at,
    )


async def change_password(user: User, old_password: str, new_password: str, db: AsyncSession) -> BaseResponse:
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

    return BaseResponse(
        date=datetime.utcnow().strftime("%d-%B-%Y"),
        status=status.HTTP_200_OK,
        message="Password updated successfully.",
        payload=None,
    )


async def update_user_bio(uuid: str, bio: str, db: AsyncSession) -> BaseResponse:
    stmt = select(User).where(User.uuid == uuid)
    result = await db.execute(stmt)
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )

    if not bio.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bio cannot be empty or whitespace."
        )

    user.bio = bio
    user.updated_at = datetime.utcnow()

    db.add(user)
    await db.commit()
    await db.refresh(user)

    return BaseResponse(
        date=datetime.utcnow().strftime("%d-%B-%Y"),
        status=status.HTTP_200_OK,
        message="User bio updated successfully.",
        payload={"bio": user.bio},
    )


async def upload_profile_picture(uuid: str, file: UploadFile, db: AsyncSession) -> BaseResponse:
    stmt = select(User).where(User.uuid == uuid)
    result = await db.execute(stmt)
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )

    file_location = f"uploads/profile_pictures/{uuid}_{file.filename}"
    try:
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error saving file: {str(e)}"
        )

    user.avatar = file_location
    user.updated_at = datetime.utcnow()

    db.add(user)
    await db.commit()
    await db.refresh(user)

    return BaseResponse(
        date=datetime.utcnow().strftime("%d-%B-%Y"),
        status=status.HTTP_200_OK,
        message="Profile picture uploaded successfully.",
        payload={"avatar_url": file_location},
    )


async def update_user_profile(uuid: str, profile_update: UpdateUser, db: AsyncSession) -> BaseResponse:
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

    return BaseResponse(
        date=datetime.utcnow().strftime("%d-%B-%Y"),
        status=status.HTTP_200_OK,
        message="User profile updated successfully.",
        payload={
            "uuid": user.uuid,
            "username": user.username,
            "email": user.email,
            "avatar": user.avatar,
            "address": user.address,
            "phone_number": user.phone_number,
            "bio": user.bio,
            "gender": user.gender,
            "date_of_birth": user.date_of_birth,
        },
    )


async def delete_user_by_uuid(uuid: str, db: AsyncSession) -> BaseResponse:
    stmt = select(User).where(User.uuid == uuid)
    result = await db.execute(stmt)
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )

    user.is_deleted = True
    user.updated_at = datetime.utcnow()

    db.add(user)
    await db.commit()

    return BaseResponse(
        date=datetime.utcnow().strftime("%d-%B-%Y"),
        status=status.HTTP_200_OK,
        message=f"User with UUID {uuid} has been marked as deleted.",
        payload={"uuid": user.uuid},
    )


async def update_user_by_uuid(uuid: str, user_update: UpdateUser, db: AsyncSession) -> BaseResponse:
    if not is_valid_uuid(uuid):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user UUID.")

    stmt = select(User).where(User.uuid == uuid)
    result = await db.execute(stmt)
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    # Apply updates
    update_data = user_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(user, key, value)

    user.updated_at = datetime.utcnow()

    db.add(user)
    await db.commit()
    await db.refresh(user)

    return BaseResponse(
        date=datetime.utcnow().strftime("%d-%B-%Y"),
        status=status.HTTP_200_OK,
        message="User updated successfully.",
        payload={
            "uuid": user.uuid,
            "username": user.username,
            "email": user.email,
            "avatar": user.avatar,
            "address": user.address,
            "phone_number": user.phone_number,
            "bio": user.bio,
            "gender": user.gender,
            "date_of_birth": format_date(user.date_of_birth),
            "is_deleted": user.is_deleted,
            "is_active": user.is_active,
            "is_verified": user.is_verified,
        }
    )


async def get_all_users(db: AsyncSession) -> BaseResponse:
    query = select(User).where(User.is_deleted == False).order_by(User.created_at.desc())
    result = await db.execute(query)
    users = result.scalars().all()

    return BaseResponse(
        date=datetime.utcnow().strftime("%d-%B-%Y"),
        status=status.HTTP_200_OK,
        message="Users retrieved successfully.",
        payload=[
            {
                "uuid": user.uuid,
                "username": user.username,
                "email": user.email,
                "avatar": user.avatar,
                "address": user.address,
                "phone_number": user.phone_number,
                "bio": user.bio,
                "gender": user.gender,
                "date_of_birth": format_date(user.date_of_birth),
                "is_deleted": user.is_deleted,
                "is_active": user.is_active,
                "is_verified": user.is_verified,
                "registered_at": user.registered_at,
            }
            for user in users
        ]
    )


async def get_user_by_uuid(uuid: str, db: AsyncSession) -> BaseResponse:
    if not is_valid_uuid(uuid):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user UUID.")

    stmt = select(User).where(User.uuid == uuid)
    result = await db.execute(stmt)
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    return BaseResponse(
        date=datetime.utcnow().strftime("%d-%B-%Y"),
        status=status.HTTP_200_OK,
        message="User retrieved successfully.",
        payload={
            "uuid": user.uuid,
            "username": user.username,
            "email": user.email,
            "avatar": user.avatar,
            "address": user.address,
            "phone_number": user.phone_number,
            "bio": user.bio,
            "gender": user.gender,
            "date_of_birth": format_date(user.date_of_birth),
            "is_deleted": user.is_deleted,
            "is_active": user.is_active,
            "is_verified": user.is_verified,
            "registered_at": user.registered_at,
        }
    )

