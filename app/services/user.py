import json
import os
import shutil
import logging

from typing import Optional, Tuple, List
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload, selectinload
from fastapi import HTTPException, status, UploadFile
from sqlalchemy import or_, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime, timedelta
from app.core.config import settings
from app.exceptions.file_exceptions import FileExtensionError, handle_file_error, FileSizeError
from app.models import UserRole, Role, UserTest
from app.models.user import User
from app.schemas.payload import BaseResponse
from app.schemas.test import PaginationMetadata, UserTestWithUserSchema
from app.schemas.user import UpdateUser, UserResponse
from app.utils.format_date import format_date
from app.utils.pagination import paginate_results
from app.utils.password import verify_password, validate_password, hash_password
from app.utils.verify import is_valid_uuid


logger = logging.getLogger(__name__)


async def fetch_all_tests(
    db: AsyncSession,
    page: int,
    page_size: int
) -> Tuple[List[UserTestWithUserSchema], PaginationMetadata]:
    try:
        query = (
            select(UserTest)
            .options(
                selectinload(UserTest.user),
                selectinload(UserTest.user_responses),
                selectinload(UserTest.assessment_type)
            )
            .where(UserTest.is_deleted == False)
            .order_by(UserTest.created_at.desc())
        )

        result = await db.execute(query)
        all_tests = result.scalars().all()

        paginated_data = paginate_results(all_tests, page, page_size)

        formatted_tests = [
            UserTestWithUserSchema(
                test_uuid=str(test.uuid),
                test_name=test.name,
                user_avatar=test.user.avatar if test.user else None,
                user_name=test.user.username if test.user else "Unknown",
                user_email=test.user.email if test.user else "Unknown",
                assessment_type_name=test.assessment_type.name if test.assessment_type else "Unknown",
                # Extract assessment type name
                response_data=[
                    json.loads(response.response_data) if isinstance(response.response_data,
                                                                     str) else response.response_data
                    for response in test.user_responses
                    if not response.is_deleted and response.response_data
                ],
                is_draft=any(response.is_draft for response in test.user_responses),
                is_completed=test.is_completed,
                created_at=test.created_at
            )
            for test in paginated_data["items"]
        ]
        metadata = PaginationMetadata(
            page=paginated_data["metadata"]["page"],
            page_size=paginated_data["metadata"]["page_size"],
            total_items=paginated_data["metadata"]["total_items"],
            total_pages=paginated_data["metadata"]["total_pages"],
        )

        return formatted_tests, metadata

    except SQLAlchemyError as e:
        logger.error(f"Database error: {e}")
        raise Exception("Error retrieving all tests.")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise Exception("An unexpected error occurred.")


async def unblock_user(uuid: str, is_blocked: bool, db: AsyncSession, current_user: User) -> BaseResponse:
    try:
        logger.info(f"Attempting to {'unblock' if not is_blocked else 'block'} user with UUID: {uuid}")

        stmt = select(User).options(joinedload(User.roles).joinedload(UserRole.role)).where(User.uuid == uuid)
        result = await db.execute(stmt)
        user = result.scalars().first()

        if not user:
            logger.warning(f"User with UUID {uuid} not found.")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found."
            )

        if user.uuid == current_user.uuid:
            logger.error("Attempt to unblock oneself.")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot unblock yourself."
            )

        if not is_blocked and any(role.role.name == "ADMIN" for role in user.roles):
            logger.error(f"Attempt to unblock admin user: {user.uuid}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin users cannot be unblocked."
            )

        user.is_blocked = is_blocked
        user.updated_at = datetime.utcnow()

        db.add(user)
        await db.commit()
        await db.refresh(user)

        logger.info(f"User {uuid} successfully {'unblocked' if not is_blocked else 'blocked'}.")
        return BaseResponse(
            date=datetime.utcnow().strftime("%d-%B-%Y"),
            status=status.HTTP_200_OK,
            message=f"User {'unblocked' if not is_blocked else 'blocked'} successfully.",
            payload={
                "uuid": user.uuid,
                "username": user.username,
                "is_blocked": user.is_blocked,
            },
        )
    except HTTPException as e:
        logger.error(f"HTTPException occurred: {e.detail}")
        raise e
    except Exception as e:
        logger.exception(f"Unexpected error occurred: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing the request."
        )


async def block_user(uuid: str, is_blocked: bool, db: AsyncSession, current_user: User) -> BaseResponse:
    try:
        logger.info(f"Attempting to {'block' if is_blocked else 'unblock'} user with UUID: {uuid}")

        stmt = select(User).options(joinedload(User.roles).joinedload(UserRole.role)).where(User.uuid == uuid)
        result = await db.execute(stmt)
        user = result.scalars().first()

        if not user:
            logger.warning(f"User with UUID {uuid} not found.")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found."
            )

        if user.uuid == current_user.uuid:
            logger.error("Attempt to block/unblock oneself.")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot block/unblock yourself."
            )

        if is_blocked and not user.is_verified:
            logger.error(f"Attempt to block unverified user: {user.uuid}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot block an unverified user."
            )

        if is_blocked and any(role.role.name == "ADMIN" for role in user.roles):
            logger.error(f"Attempt to block admin user: {user.uuid}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin users cannot be blocked."
            )

        user.is_blocked = is_blocked
        user.updated_at = datetime.utcnow()

        db.add(user)
        await db.commit()
        await db.refresh(user)

        logger.info(f"User {uuid} successfully {'blocked' if is_blocked else 'unblocked'}.")
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
    except HTTPException as e:
        logger.error(f"HTTPException occurred: {e.detail}")
        raise e
    except Exception as e:
        logger.exception(f"Unexpected error occurred: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing the request."
        )


async def get_user_by_email(email: str, db: AsyncSession, current_user: User) -> UserResponse:

    if current_user.email != email and not any(role.role.name == "ADMIN" for role in current_user.roles):
        raise HTTPException(status_code=403, detail="Permission denied.")

    stmt = (
        select(User)
        .options(joinedload(User.roles).joinedload(UserRole.role))
        .where(User.email == email)
    )
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
        is_blocked=user.is_blocked,
    )


async def change_password(user: User, old_password: str, new_password: str, db: AsyncSession) -> BaseResponse:

    if not verify_password(old_password, user.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Old password is incorrect."
        )

    validate_password(new_password)

    if verify_password(new_password, user.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from the old password."
        )

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
    try:
        extension = file.filename.split(".")[-1].lower()
        if extension not in settings.ALLOWED_EXTENSIONS:
            raise FileExtensionError(settings.ALLOWED_EXTENSIONS)

        file_size = file.file.seek(0, os.SEEK_END)
        file.file.seek(0)
        if file_size > settings.MAX_FILE_SIZE:
            raise FileSizeError(settings.MAX_FILE_SIZE)

        stmt = select(User).where(User.uuid == uuid)
        result = await db.execute(stmt)
        user = result.scalars().first()

        if not user:
            raise HTTPException(status_code=404, detail="User not found.")

        upload_folder = os.path.join(settings.BASE_UPLOAD_FOLDER, "profile_pictures")
        os.makedirs(upload_folder, exist_ok=True)

        file_name = f"{uuid}_{file.filename}"
        file_path = os.path.join(upload_folder, file_name)
        try:
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error saving file: {str(e)}")

        avatar_url = f"{settings.BASE_UPLOAD_FOLDER}/profile_pictures/{file_name}"
        user.avatar = avatar_url
        user.updated_at = datetime.utcnow()

        db.add(user)
        await db.commit()
        await db.refresh(user)

        return BaseResponse(
            date=datetime.utcnow().strftime("%Y-%m-%d"),
            status=200,
            message="Profile picture uploaded successfully.",
            payload={"avatar_url": avatar_url},
        )

    except (FileExtensionError, FileSizeError) as e:
        raise handle_file_error(e)
    except HTTPException as e:
        raise e
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred: {str(e)}"
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

    # Validate date_of_birth
    if "date_of_birth" in update_data:
        date_of_birth = update_data["date_of_birth"]

        if date_of_birth > datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="date_of_birth cannot be in the future."
            )

        min_age_date = datetime.utcnow() - timedelta(days=13 * 365)
        if date_of_birth > min_age_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User must be at least 13 years old."
            )

    # Update user attributes
    for key, value in update_data.items():
        setattr(user, key, value)

    user.updated_at = datetime.utcnow()

    # Persist changes
    db.add(user)
    await db.commit()
    await db.refresh(user)  # Refresh after commit to avoid closed transaction error

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


async def delete_user_by_uuid(uuid: str, db: AsyncSession, current_user: User) -> BaseResponse:
    stmt = (
        select(User)
        .options(joinedload(User.roles).joinedload(UserRole.role))  # Eager load roles
        .where(User.uuid == uuid, User.is_deleted == False)
    )
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
            detail="You cannot delete yourself."
        )

    if any(role.role.name == "ADMIN" for role in user.roles):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin users cannot be deleted."
        )

    user.is_deleted = True
    user.updated_at = datetime.utcnow()

    db.add(user)
    await db.commit()
    await db.refresh(user)

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


async def get_all_users(
    db: AsyncSession,
    search: Optional[str] = None,
    sort_by: Optional[str] = "created_at",
    sort_order: Optional[str] = "asc",
    page: int = 1,
    page_size: int = 10,
    filters: dict = None
):
    try:
        stmt = (
            select(User)
            .where(User.is_deleted == False)
            .options(joinedload(User.roles).joinedload(UserRole.role))
            .distinct()
        )

        if search:
            search_filter = or_(
                User.username.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%"),
                User.bio.ilike(f"%{search}%")
            )
            stmt = stmt.where(search_filter)

        if filters:
            for field, value in filters.items():
                if value is not None and hasattr(User, field):
                    stmt = stmt.where(getattr(User, field) == value)

        stmt = stmt.where(~User.roles.any(UserRole.role.has(Role.name == "ADMIN")))

        if hasattr(User, sort_by):
            sort_column = getattr(User, sort_by)
            stmt = stmt.order_by(desc(sort_column) if sort_order.lower() == "desc" else asc(sort_column))
        else:
            stmt = stmt.order_by(User.created_at.desc())

        result = await db.execute(stmt)
        users = result.unique().scalars().all()

        paginated_users = paginate_results(users, page, page_size)

        response_payload = [
            {
                "uuid": user.uuid,
                "username": user.username,
                "email": user.email,
                "bio": user.bio,
                "gender": user.gender,
                "avatar": user.avatar,
                "is_active": user.is_active,
                "is_verified": user.is_verified,
                "created_at": user.created_at.strftime("%d-%B-%Y"),
                "is_blocked": user.is_blocked
            }
            for user in paginated_users["items"]
        ]

        return {
            "users": response_payload,
            "metadata": paginated_users["metadata"]
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while retrieving users: {str(e)}"
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
            "is_blocked": user.is_blocked
        }
    )

